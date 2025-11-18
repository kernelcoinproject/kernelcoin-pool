# kernelcoin-pool
MiningCore Pool hosted at https://pool.kernelcoin.org

## Screenshots
<img width="1214" height="689" alt="Screenshot 2025-11-18 at 3 18 56 PM" src="https://github.com/user-attachments/assets/6cbd67c1-d6ab-439e-b674-811e111670ae" />

## Basic Setup

Get yourself a cloud hosted vm (ubuntu 24.04) and connect via ssh

As non root user

1. Setup kernelcoind

```
mkdir -p kernelcoin
cd kernelcoin
wget https://github.com/kernelcoinproject/kernelcoin/releases/download/main/kernelcoin-0.21.4-x86_64-linux-gnu.tar.gz
tar xf kernelcoin-0.21.4-x86_64-linux-gnu.tar.gz
```

```
mkdir -p ~/.kernelcoin
cat > ~/.kernelcoin/kernelcoin.conf << EOF
# enable p2p
listen=1
txindex=1
logtimestamps=1
server=1
rpcuser=mike
rpcpassword=x
rpcport=9332
rpcallowip=127.0.0.1
rpcbind=127.0.0.1
EOF
```

```
./kernelcoind
```
```
./kernelcoin-cli createwallet "main"
./kernelcoin-cli getnewaddress "" legacy
```

2. Download and run the website binary

```
cd ~
mkdir -p website
cd website
wget https://github.com/kernelcoinproject/kernelcoin-charity/releases/download/main/website.tar.gz
tar xf website.tar.gz
```


3. Setup caddy to host via https without username and password

As root
```
mkdir -p /opt/caddy
cd /opt/caddy
wget https://github.com/caddyserver/caddy/releases/download/v2.10.2/caddy_2.10.2_linux_amd64.tar.gz
tar xf caddy_2.10.2_linux_amd64.tar.gz
```

```
DOMAIN="website.duckdns.org"
cat > /opt/caddy/Caddyfile << EOF
$DOMAIN {

    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    encode gzip

    log {
        output file /var/log/caddy/wallet.log {
            roll_size 100mb
            roll_keep 5
        }
        format json
    }

    reverse_proxy 127.0.0.1:8080
}
EOF
/opt/caddy/caddy run
```

4. Setup the proxy
As non root user
```
mkdir -p /home/ubuntu/proxy
cd /home/ubuntu/proxy
wget https://raw.githubusercontent.com/kernelcoinproject/kernelcoin-pool/refs/heads/main/proxy.py
sudo apt install -y python3-aiohttp
```

5. Setup MiningCore and postgresql
Install deps
```
apt install -y git cmake build-essential libssl-dev pkg-config libboost-all-dev libsodium-dev libzmq5 nano tzdata postgresql
```
Install dotnet sdk 6

```
wget https://builds.dotnet.microsoft.com/dotnet/Sdk/6.0.428/dotnet-sdk-6.0.428-linux-x64.tar.gz
sudo mkdir /usr/share/dotnet
sudo tar xzf dotnet-sdk-6.0.428-linux-x64.tar.gz -C /usr/share/dotnet
sudo ln -s /usr/share/dotnet/dotnet /usr/bin/dotnet

echo "export DOTNET_ROOT=/usr/share/dotnet" >> ~/.bashrc
echo "export DOTNET_BUNDLE_EXTRACT_BASE_DIR=/tmp/dotnet" >> ~/.bashrc
source ~/.bashrc
dotnet --info
```

Build miningcore
```
git clone https://github.com/oliverw/miningcore.git
cd miningcore/src/Miningcore
BUILDIR=${1:-../../build}
echo "Building into $BUILDIR"
dotnet publish -c Release --framework net6.0 -o $BUILDIR
```

Configure postgresql
```
sudo chmod 777 /home/ubuntu/miningcore/src/Miningcore/Persistence/Postgres/Scripts/createdb.sql
su postgres
psql
CREATE ROLE miningcore WITH LOGIN ENCRYPTED PASSWORD 'your-secure-password';
CREATE DATABASE miningcore OWNER miningcore;
\q
psql -d miningcore -f /home/ubuntu/miningcore/src/Miningcore/Persistence/Postgres/Scripts/createdb.sql
exit
```

Create kernelcoin.json update wallet address
```
cat > /home/ubuntu/miningcore/kernelcoin.json << EOF
{
  "api": {
      "enabled": true,
      "listenAddress": "127.0.0.1",
      "port": 4000,
      "rateLimit": {
        "disabled": true
      }
  },

  "logging": {
    "level": "info",
    "enableConsoleLog": true,
    "enableConsoleColors": true,
    "logDirectory": "logs"
  },

  "banning": {
    "enabled": false
  },

  "notifications": {
    "enabled": false
  },

  "persistence": {
    "postgres": {
      "host": "127.0.0.1",
      "port": 5432,
      "user": "miningcore",
      "password": "your-secure-password",
      "database": "miningcore"
    }
  },

  "paymentProcessing": {
    "enabled": true,
    "interval": 600,
    "shareRecoveryFile": "recovered-shares.txt"
  },

  "pools": [
    {
      "id": "kernelcoin",
      "enabled": true,

      "coin": "kernelcoin",

      "address": "KGQQeiBxQX1LffakKcypjyqtrRQETGKjju",

      "addressPrefixes": {
        "pubkey": [45],
        "script": [23, 25],
        "bech": "kcn"
      },

      "jobRebroadcastTimeout": 10,
      "blockRefreshInterval": 1000,
      "clientConnectionTimeout": 600,

      "blockTemplateRpcExtraParameters": {
        "rules": ["segwit", "mweb"]
      },

      "ports": {
        "3333": {
          "listenAddress": "0.0.0.0",
          "difficulty": 0.1,
          "name": "CPU/GPU Mining",
          "varDiff": {
            "minDiff": 0.1,
            "maxDiff": 50,
            "targetTime": 15,
            "retargetTime": 60,
            "variancePercent": 30
          }
        }
      },

      "daemons": [
        {
          "host": "127.0.0.1",
          "port": 9333,
          "user": "mike",
          "password": "x"
        }
      ],

      "coreWallet": {
        "host": "127.0.0.1",
        "port": 9333,
        "user": "mike",
        "password": "x"
      },

      "paymentProcessing": {
        "enabled": true,
        "minimumPayment": 1,
        "payoutScheme": "PPLNS",
        "payoutSchemeConfig": {
          "factor": 2.0
        }
      }
    }
  ]
}
EOF
```
Modify miningcore to know about kernelcoin

```
sed -i '1r /dev/stdin' /home/ubuntu/minigcore/build/coins.json <<'EOF'
"kernelcoin": {
    "name": "Kernelcoin",
    "canonicalName": "Kernelcoin",
    "symbol": "KCN",
    "family": "bitcoin",
    "website": "",
    "market": "",
    "twitter": "",
    "telegram": "",
    "discord": "",

    "coinbaseHasher": {
        "hash": "sha256d"
    },

    "headerHasher": {
        "hash": "scrypt",
        "args": [
            1024,
            1
        ]
    },

    "blockHasher": {
        "hash": "reverse",
        "args": [
            {
                "hash": "sha256d"
            }
        ]
    },

    "posBlockHasher": {
        "hash": "reverse",
        "args": [
            {
                "hash": "scrypt",
                "args": [
                    1024,
                    1
                ]
            }
        ]
    },

    "shareMultiplier": 65536,

    "addressPrefixes": {
        "pubkey": [45],
        "script": [23, 25],
        "bech": "kcn"
    }
},
EOF
```
Give Miningcore a test (proxy and kernelcoind is off)
```
cd /home/ubuntu/miningcore
./build/Miningcore -c kernelcoin.json
```

6. Run it all at boot via tmux

Run as root user (port 443 requires root)
```
yum install -y tmux cronie
cat > /root/startWeb.sh << EOF
tmux kill-session -t caddy 2>/dev/null
tmux new -s caddy -d
tmux send-keys -t caddy "cd /opt/caddy && ./caddy run" C-m
EOF
chmod +x /root/startWeb.sh
```

Run as root user
```
crontab -e
@reboot /root/startWeb.sh
```

Run as non-root user
```

cat > /home/ubuntu/start.sh << EOF
tmux kill-session -t p 2>/dev/null
tmux new -s p -d
tmux neww -t p -n kernelcoin
tmux neww -t p -n server
tmux neww -t p -n proxy
tmux neww -t p: -n web
tmux send-keys -t p:kernelcoin "cd /home/ubuntu/kernelcoin && ./kernelcoind" C-m
tmux send-keys -t p:server "bash" C-m
tmux send-keys -t p:server "cd /home/ubuntu/miningcore && ./build/Miningcore -c kernelcoin.json" C-m
tmux send-keys -t p:proxy "cd /home/ubuntu/proxy && python3 proxy.py" C-m
tmux send-keys -t p:web "cd /home/ubuntu/website && ./website" C-m
EOF
chmod +x /home/ubuntu/start.sh
```

Run as non-root user
```
crontab -e
@reboot /home/ubuntu/start.sh
```


