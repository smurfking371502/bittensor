import os
import sys
import time
import threading
import hashlib
import json
from abc import ABC, abstractmethod
from typing import Tuple

import yaml
import requests
import bittensor as bt

from redteam_core.protocol import Commit
from redteam_core import MainConfig

from .config import MinerMainConfig


class BaseMiner(ABC):
    def __init__(self):
        self.config = MainConfig()
        self.miner_config: MinerMainConfig = MinerMainConfig()
        self.setup_logging()
        self.setup_bittensor_objects()
        self.axon.attach(self.forward, self.blacklist)
        self.is_running = False

    def setup_logging(self):
        bt.logging.enable_default()
        bt.logging.enable_info()
        if self.config.BITTENSOR.LOGGING_LEVEL == "DEBUG":
            bt.logging.enable_debug()
        elif self.config.BITTENSOR.LOGGING_LEVEL == "TRACE":
            bt.logging.enable_trace()
        bt.logging.info(
            f"Running miner for subnet:  {self.config.BITTENSOR.SUBNET_NETUID} on network: {self.config.BITTENSOR.SUBTENSOR_NETWORK} with config:"
        )
        bt.logging.info(self.config.model_dump_json())

    def setup_bittensor_objects(self):
        bt.logging.info("Setting up Bittensor objects.")

        bt_config = self._create_bittensor_config()

        self.wallet = bt.wallet(config=bt_config)
        bt.logging.info(f"Wallet: {self.wallet}")

        self.subtensor = bt.subtensor(config=bt_config)
        bt.logging.info(f"Subtensor: {self.subtensor}")

        self.dendrite = bt.dendrite(wallet=self.wallet)
        bt.logging.info(f"Dendrite: {self.dendrite}")

        self.metagraph = self.subtensor.metagraph(self.config.BITTENSOR.SUBNET_NETUID)
        bt.logging.info(f"Metagraph: {self.metagraph}")

        self.axon = bt.axon(wallet=self.wallet, port=self.miner_config.AXON_PORT)
        bt.logging.info(f"Axon: {self.axon}")

        if self.wallet.hotkey.ss58_address not in self.metagraph.hotkeys:
            bt.logging.error(
                f"\nYour miner: {self.wallet} is not registered to chain connection: {self.subtensor} \nRun 'btcli register' and try again."
            )
            exit()
        else:
            self.my_subnet_uid = self.metagraph.hotkeys.index(
                self.wallet.hotkey.ss58_address
            )
            bt.logging.info(f"Running miner on uid: {self.my_subnet_uid}")

    def run(self):
        # Check that miner is registered on the network.
        self.metagraph.sync(subtensor=self.subtensor)
        last_sync = time.time()

        # Serve passes the axon information to the network + netuid we are hosting on.
        # This will auto-update if the axon port of external ip have changed.
        bt.logging.info(
            f"Serving miner axon {self.axon} on network: {self.config.BITTENSOR.SUBTENSOR_NETWORK} with netuid: {self.config.BITTENSOR.SUBNET_NETUID}"
        )
        self.axon.serve(
            netuid=self.config.BITTENSOR.SUBNET_NETUID, subtensor=self.subtensor
        )

        # Start  starts the miner's axon, making it active on the network.
        self.axon.start()

        while True:
            RESYNC_INTERVAL = 600  # resync every 10 minutes
            SLEEP_TIME = 30

            try:
                if time.time() - last_sync > RESYNC_INTERVAL:
                    bt.logging.info("Resyncing metagraph...")
                    self.metagraph.sync(subtensor=self.subtensor)
                    bt.logging.info(
                        f"Resynced metagraph Block: {self.metagraph.block.item()}"
                    )
                    last_sync = time.time()
                time.sleep(SLEEP_TIME)

            except KeyboardInterrupt:
                self.axon.stop()
                bt.logging.success("Miner killed by keyboard interrupt.")
                break
            except Exception as e:
                bt.logging.error(f"Miner exception: {e}")

    def run_in_background_thread(self):
        """
        Starts the miner's operations in a separate background thread.
        This is useful for non-blocking operations.
        """
        if not self.is_running:
            bt.logging.debug("Starting miner in background thread.")
            self.should_exit = False
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            self.is_running = True
            bt.logging.debug("Started")

    def stop_run_thread(self):
        """
        Stops the miner's operations that are running in the background thread.
        """
        if self.is_running:
            bt.logging.debug("Stopping miner in background thread.")
            self.should_exit = True
            self.thread.join(5)
            self.is_running = False
            bt.logging.debug("Stopped")

    def __enter__(self):
        """
        Starts the miner's operations in a background thread upon entering the context.
        This method facilitates the use of the miner in a 'with' statement.
        """
        self.run_in_background_thread()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Stops the miner's background operations upon exiting the context.
        This method facilitates the use of the miner in a 'with' statement.

        Args:
            exc_type: The type of the exception that caused the context to be exited.
                      None if the context was exited without an exception.
            exc_value: The instance of the exception that caused the context to be exited.
                       None if the context was exited without an exception.
            traceback: A traceback object encoding the stack trace.
                       None if the context was exited without an exception.
        """
        self.stop_run_thread()

    def _get_active_challenges(self):
        active_challenges_path = "https://raw.githubusercontent.com/RedTeamSubnet/RedTeam/refs/heads/main/redteam_core/challenge_pool/active_challenges.yaml"
        response = requests.get(active_challenges_path)
        active_challenges = yaml.load(response.text, yaml.FullLoader)
        active_challenges = list(active_challenges.keys())
        bt.logging.info(f"Active challenges: {active_challenges}")
        return active_challenges

    def _create_bittensor_config(self) -> bt.Config:
        """
        Create a Bittensor Config object from MainConfig.

        Maps the hierarchical MainConfig structure to Bittensor's expected Config format.

        Returns:
            bt.Config: Bittensor configuration object
        """
        bt_config = bt.Config()
        # Set wallet configuration
        if bt_config.wallet is None:
            bt_config.wallet = bt.Config()

        bt_config.wallet.path = self.miner_config.WALLET_DIR
        bt_config.wallet.name = self.miner_config.WALLET_NAME
        bt_config.wallet.hotkey = self.miner_config.HOTKEY_NAME

        if bt_config.subtensor is None:
            bt_config.subtensor = bt.Config()
        # Set subtensor configuration
        bt_config.subtensor.network = self.config.BITTENSOR.SUBTENSOR_NETWORK

        # Set netuid (subnet configuration)
        bt_config.netuid = self.config.BITTENSOR.SUBNET_NETUID

        return bt_config

    def _get_miner_auth_headers(self, body: dict) -> dict:
        timestamp = str(time.time_ns())
        body_str = json.dumps(body)
        body_hash = hashlib.sha256(body_str.encode("utf-8")).hexdigest()

        message = f"{body_hash}.{timestamp}"
        signature = f"0x{self.wallet.hotkey.sign(message).hex()}"

        return {
            "miner-uid": str(self.my_subnet_uid),
            "miner-hotkey": self.wallet.hotkey.ss58_address,
            "timestamp": timestamp,
            "signature": signature,
            "Content-Type": "application/json",
        }

    def verify_docker_hub_credentials(self, username: str, pat: str) -> bool:
        try:
            response = requests.get(
                "https://hub.docker.com/v2/users/login/",
                json={"username": username, "password": pat},
                timeout=10,
            )
            if response.status_code == 200:
                return True

            print(f"Docker Hub verification failed: {response.status_code}")
            return False
        except Exception as e:
            print(f"Error connecting to Docker Hub: {e}")
            return False

    def is_dockerhub_repo_private(
        self, username: str, repo_name: str, pat: str
    ) -> bool:
        try:
            url = f"https://registry-1.docker.io/v2/{username}/{repo_name}/tags/list"
            response = requests.get(url)

            if response.status_code == 200:
                return False
            elif response.status_code == 401:
                return True
            elif response.status_code == 404:
                return False
            else:
                bt.logging.error(
                    f"Unexpected response from Docker Hub: {response.status_code}"
                )
                return False
        except Exception as e:
            bt.logging.error(f"Error checking repository visibility: {e}")
            return False

    def verify_and_sync_docker_info(self, username: str):
        pat_path = self.miner_config.PAT_FILE_PATH
        if not os.path.exists(pat_path):
            bt.logging.critical(f"PAT file not found at {pat_path}. Cannot proceed.")
            sys.exit(1)

        with open(pat_path, "r") as f:
            pat = f.read().strip()

        bt.logging.info(f"Verifying PAT for Docker Hub user: {username}...")
        if not self.verify_docker_hub_credentials(username, pat):
            bt.logging.critical(
                f"Docker Hub PAT verification failed for {username}. Exiting."
            )
            sys.exit(1)

        bt.logging.success("Docker Hub PAT verified.")

        payload = {"personal_access_token": pat, "dockerhub_username": username}
        headers = self._get_miner_auth_headers(payload)

        try:
            url = f"{self.config.STORAGE_API_URL}/miner/docker-info"
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            bt.logging.success("Docker info synced to storage successfully.")
        except Exception as e:
            bt.logging.critical(f"Failed to sync Docker info to storage: {e}")
            sys.exit(1)

    @abstractmethod
    def forward(self, synapse: Commit) -> Commit: ...

    @abstractmethod
    def blacklist(self, synapse: Commit) -> Tuple[bool, str]: ...
