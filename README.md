# RedTeam subnet - Miner (Agent)

This repository is for miner of RedTeam subnet. It is focused on running miner axon node for submitting challenge solutions to RedTeam subnet. For developing challenges please use dedicated repositories and separate machine to prevent submission stealing as your public ip is accessible in a [bittensor metagraph](https://taostats.io/subnets/61/metagraph).

## ✨ Features

- Miner node
- Independent
- Easy configuration
- Dockerized setup
- Docker Compose support

---

## Getting Started

### 1. 🚧 Prerequisites

- Prepare miner wallet (skip if you already have one):
    - Install **Bittensor CLI**:
        - [Installing Bittensor CLI](https://docs.learnbittensor.org/getting-started/install-btcli)
        - [Bittensor CLI: `btcli` Reference Document](https://docs.learnbittensor.org/btcli)
    - Create miner wallet:
        - [Working with Keys](https://docs.learnbittensor.org/keys/working-with-keys)
        - [Bittensor CLI Permissions](https://docs.learnbittensor.org/btcli/btcli-permissions)
    - Register miner wallet to RedTeam subnet:
        - [Mining in Bittensor](https://docs.learnbittensor.org/miners)
        - [Miner's Guide to `BTCLI`](https://docs.learnbittensor.org/miners/miners-btcli-guide)
- Install [**docker** and **docker compose**](https://docs.docker.com/engine/install)
    - Docker [intstallation script](https://github.com/docker/docker-install)
    - Docker [post-installation steps](https://docs.docker.com/engine/install/linux-postinstall)
- Prepare your own challenge commit as solution for RedTeam subnet challenges:
    - Choose challenges to solve from [RedTeam subnet - Docs](https://docs.theredteam.io).
    - Implement your own solution for the challenges.
    - Build and push docker image to Docker Hub.
    - Get the commit hash of your pushed docker image.

---

### 2. 📥 Download or clone the repository

**2.1.** Prepare projects directory (if not exists):

```sh
# Create projects directory:
mkdir -pv ~/workspaces/projects

# Enter into projects directory:
cd ~/workspaces/projects
```

**2.2.** Follow one of the below options **[A]** or **[B]**:

**OPTION A.** Clone the repository:

```sh
git clone https://github.com/RedTeamSubnet/miner.git && \
    cd miner
```

**OPTION B.** Download source code:

1. Download archived **zip** or **tar.gz** file from [**releases**](https://github.com/RedTeamSubnet/miner/releases).
2. Extract it into the projects directory.
3. Enter into the extracted project directory.

### 3. 🔧 Configure active commit file

**[IMPORTANT]** Make sure to change the **commit hash** to your own value in the **`active_commit.yaml`** file:

```sh
# Copy template active commit file:
cp -v ./templates/configs/active_commit.yaml ./volumes/configs/agent-miner/active_commit.yaml
cp -v ./templates/configs/personal_access_token.txt ./volumes/configs/agent-miner/personal_access_token.txt
```

### 4. Update commit file and personal access token file

1. Update the **commit hash** in the **`active_commit.yaml`** file to your own value.

    ```sh
        # Edit active commit file to fit in your environment
        nano ./volumes/configs/agent-miner/active_commit.yaml
    ```

2. Update the **personal access token** in the **`personal_access_token.txt`** file to your own value.

    ```sh
        # Edit personal access token file to fit in your environment
        nano ./volumes/configs/agent-miner/personal_access_token.txt
    ```

### 4. 🌎 Configure environment variables

[NOTE] Please, check **[environment variables](#-environment-variables)** section for more details.

**[IMPORTANT]** Make sure to change the **wallet directory and wallet name variables** to your own values in the **`.env`** file:

```sh
# Copy '.env.example' file to '.env' file:
cp -v ./.env.example ./.env

# Edit environment variables to fit in your environment
nano ./.env
```

### 5. ✅ Check configuration

```sh
## Check docker compose configuration is valid:
./compose.sh validate
# Or:
docker compose config
```

### 6. 🏁 Run miner node

```sh
## Start docker compose:
./compose.sh start -l
# Or:
docker compose up -d --remove-orphans --force-recreate && \
    docker compose logs -f --tail 100
```

### (OPTIONAL) 🛑 Stop miner node

```sh
# Stop docker compose:
./compose.sh stop
# Or:
docker compose down --remove-orphans
```

👍

---

## ⚙️ Configuration

### 🌎 Environment Variables

[**`.env.example`**](./.env.example):

```sh
## --- Environment variable --- ##
ENV=PRODUCTION
DEBUG=false
# TZ=UTC
# PYTHONDONTWRITEBYTECODE=1


## -- Bittensor configs -- ##
# RT_BT_SUBTENSOR_NETWORK="wss://entrypoint-finney.opentensor.ai:443"


## -- Subnet configs -- ##
# ! WARNING: Do not use `~` character, it will not be expand properly! Use absolute path or ${HOME} instead:
RT_BTCLI_WALLET_DIR="${HOME}/.bittensor/wallets" # !!! CHANGE THIS TO REAL WALLET DIRECTORY !!!
# RT_BT_SUBNET_NETUID=61


## - Miner configs -- ##
RT_MINER_COMMIT_FILE_PATH="./volumes/configs/agent-miner/active_commit.yaml" # !!! CHANGE THIS TO REAL COMMIT FILE PATH !!!
RT_MINER_WALLET_NAME="miner" # !!! CHANGE THIS TO REAL MINER WALLET NAME !!!
RT_MINER_HOTKEY_NAME="default" # !!! CHANGE THIS TO REAL MINER HOTKEY NAME !!!
RT_MINER_AXON_PORT=8091
# RT_MINER_LOGS_DIR="/var/log/agent-miner"
# RT_MINER_DATA_DIR="/var/lib/agent-miner"
```

### 🔧 Template active commit file

[**`active_commit.yaml`**](./volumes/configs/agent-miner/active_commit.yaml):

```yaml
- ab_sniffer_v4---redteamsubnet61/template-ab_sniffer_v4@sha256:a5fff733d574ae0c9c93d9029a7fc2aaaeeac07793fb6ef4683236579f1bf857
- ada_detection_v1---redteamsubnet61/template-ada_detection_v1@sha256:5b468ec48eae57907f1ba91de12bfe78f709351b0421e14a3b105dcb00844103
- humanize_behaviou_v4---redteamsubnet61/template-humanize_behaviou_v4@sha256:f84f4d5a179908214121e071906357ddbfaee30fb6da2e896d404fc00acd20e3
```

## 📚 Documentation

- <https://docs.theredteam.io>

---

## 📑 References

- Bittensor docs: <https://docs.learnbittensor.org>
- Bittensor CLI: <https://docs.learnbittensor.org/btcli>
- Bittensor CLI GitHub: <https://github.com/opentensor/btcli>
- Bittensor CLI PyPI: <https://pypi.org/project/bittensor-cli>
- The RedTeam subnet: <https://www.theredteam.io>
