import os
import sys
import pathlib
import pickle
from typing import Tuple

import yaml
import bittensor as bt
import redteam_core
from redteam_core import Commit

from ._base import BaseMiner


class Miner(BaseMiner):
    def __init__(self):
        super().__init__()
        self.active_challenges = self._get_active_challenges()
        self.synapse_commit = self._load_synapse_commit()
        self._verify_docker_info()

    def forward(self, synapse: Commit) -> Commit:
        active_commits = self._load_active_commit()
        served_commits = list(self.synapse_commit.commit_dockers.keys())
        for commit in active_commits:
            if commit not in served_commits:
                self.synapse_commit.add_encrypted_commit(commit)
        bt.logging.info(f"Synapse commit: {self.synapse_commit}")
        self.synapse_commit.reveal_if_ready()
        self._save_synapse_commit()
        synapse_response = self.synapse_commit._hide_secret_info()
        return synapse_response

    def blacklist(self, synapse: Commit) -> Tuple[bool, str]:
        hotkey = synapse.dendrite.hotkey
        uid = self.metagraph.hotkeys.index(hotkey)
        stake = self.metagraph.S[uid]
        bt.logging.info(f"Validator with the hotkey {hotkey} is querying your node")
        if stake < self.config.MIN_VALIDATOR_STAKE:
            bt.logging.warning(
                f"Validator with the hotkey {hotkey} has been blacklisted"
            )
            return True, "Not enough stake"
        return False, "Passed"

    def _load_synapse_commit(self) -> Commit:
        commit_file = self.miner_config.COMMIT_STORAGE_DIR + "/commit.pkl"
        if not os.path.exists(commit_file):
            return Commit()
        with open(commit_file, "rb") as f:
            commit = pickle.load(f)
        return commit

    def _save_synapse_commit(self):
        commit_file = self.miner_config.COMMIT_STORAGE_DIR + "/commit.pkl"
        os.makedirs(self.miner_config.COMMIT_STORAGE_DIR, exist_ok=True)
        with open(commit_file, "wb") as f:
            pickle.dump(self.synapse_commit, f)

    def _load_active_commit(self) -> list:
        commit_file = self.miner_config.ACTIVE_COMMIT_FILE
        if not os.path.exists(commit_file):
            bt.logging.critical(f"Active commit file not found at {commit_file}")
            sys.exit(1)
        
        with open(commit_file, "r") as f:
            commits = yaml.load(f, yaml.FullLoader)

        if commits is None:
            return []

        valid_commits = self._check_format_commits(commits)

        return valid_commits

    def _extract_single_docker_username(self) -> str:
        commits = self._load_active_commit()
        usernames = set()
        for commit in commits:
            _, docker_info = commit.split("---")
            docker_id, _ = docker_info.split("@sha256:")
            if "/" in docker_id:
                usernames.add(docker_id.split("/")[0])

        if len(usernames) == 0:
            bt.logging.critical("No Docker Hub username found in active_commit.yaml")
            sys.exit(1)
        if len(usernames) > 1:
            bt.logging.critical(f"Multiple Docker Hub usernames found: {usernames}. Only one allowed.")
            sys.exit(1)

        return list(usernames)[0]

    def _verify_docker_info(self):
        username = self._extract_single_docker_username()
        self.verify_and_sync_docker_info(username)
        self._verify_commits_private(username)

    def _verify_commits_private(self, username: str):
        pat_path = self.miner_config.PAT_FILE_PATH
        if not os.path.exists(pat_path):
            bt.logging.critical(f"PAT file not found at {pat_path}. Cannot verify repos.")
            sys.exit(1)

        with open(pat_path, "r") as f:
            pat = f.read().strip()

        commits = self._load_active_commit()
        for commit in commits:
            _, docker_info = commit.split("---")
            docker_id, _ = docker_info.split("@sha256:")
            if "/" not in docker_id:
                bt.logging.warning(f"Skipping commit with no repository path: {commit}")
                continue
            
            repo_name = docker_id.split("/")[1]
            if not self.is_dockerhub_repo_private(username, repo_name, pat):
                bt.logging.critical(f"Repository {repo_name} is public! Only private repos allowed. Exiting.")
                sys.exit(1)

        bt.logging.success("All commits are from private Docker Hub repositories.")

    def _get_active_challenges(self) -> dict:
        """Load active_challenges.yaml from redteam_core package"""

        redteam_core_path = pathlib.Path(redteam_core.__file__).parent
        yaml_file = redteam_core_path / "challenge_pool" / "active_challenges.yaml"
        with open(yaml_file) as f:
            active_challenges_yml = yaml.load(f, yaml.FullLoader)
            active_challenges = list(active_challenges_yml.keys())
        bt.logging.info(f"Active challenges: {active_challenges}")
        return active_challenges

    def _check_format_commits(self, commits: list) -> list[str]:
        # Validate commit format
        valid_commits = []
        for commit in commits:
            if not isinstance(commit, str):
                bt.logging.warning(f"Invalid commit format (not a string): {commit}")
                continue

            # Check if commit follows the format: challenge_name---dockerhub_id@sha256:hash
            if not commit.count("---") == 1 or not commit.count("@sha256:") == 1:
                bt.logging.warning(f"Invalid commit format: {commit}")
                continue

            challenge_name, docker_info = commit.split("---")
            docker_id, sha = docker_info.split("@sha256:")

            if not challenge_name or not docker_id or not sha:
                bt.logging.warning(f"Invalid commit format (missing parts): {commit}")
                continue

            if challenge_name not in self.active_challenges:
                bt.logging.warning(
                    f"Invalid commit format (challenge not active): {commit}"
                )
                continue

            valid_commits.append(commit)
        return valid_commits


__all__ = [
    "Miner",
]
