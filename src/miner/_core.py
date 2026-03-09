import os
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

        _current_path = pathlib.Path(__file__).parent.resolve()
        commit_file = _current_path / "config" / "active_commit.yaml"
        commits = yaml.load(open(commit_file), yaml.FullLoader)

        if commits is None:
            return []

        valid_commits = self._check_format_commits(commits)

        return valid_commits

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
