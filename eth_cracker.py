# eth_cracker.py
import os
import requests
import logging
import time
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
from dotenv import load_dotenv

# Constants
LOG_FILE_NAME = "eth_cracker.log"
WALLETS_FILE_NAME = "eth_wallets_with_balance.txt"

# Global counter for the number of wallets scanned
wallets_scanned = 0

# Get the absolute path of the directory where the script is located
directory = os.path.dirname(os.path.abspath(__file__))
# Initialize directory paths
log_file_path = os.path.join(directory, LOG_FILE_NAME)
wallets_file_path = os.path.join(directory, WALLETS_FILE_NAME)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),  # Log to a file
        logging.StreamHandler(),  # Log to standard output
    ],
)

# Load environment variables from .env file
load_dotenv()

def bip44_ETH_wallet_from_seed(seed):
    # Generate the seed from the mnemonic
    seed_bytes = Bip39SeedGenerator(seed).Generate()

    # Create a Bip44 object for Ethereum derivation
    bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM)

    # Derive the account 0, change 0, address_index 0 path (m/44'/60'/0'/0/0)
    bip44_acc_ctx = (
        bip44_mst_ctx.Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(0)
    )

    # Get the Ethereum address
    return bip44_acc_ctx.PublicKey().ToAddress()


def check_ETH_balance(address, etherscan_api_key, retries=3, delay=5):
    # Etherscan API endpoint to check the balance of an address
    api_url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest&apikey={etherscan_api_key}"

    for attempt in range(retries):
        try:
            # Make a request to the Etherscan API
            response = requests.get(api_url)
            data = response.json()

            # Check if the request was successful
            if data["status"] == "1":
                # Convert Wei to Ether (1 Ether = 10^18 Wei)
                balance = int(data["result"]) / 1e18
                return balance
            else:
                logging.error("Error getting balance: %s", data["message"])
                return 0
        except Exception as e:
            if attempt < retries - 1:
                logging.error(
                    f"Error checking balance, retrying in {delay} seconds: {str(e)}"
                )
                time.sleep(delay)
            else:
                logging.error("Error checking balance: %s", str(e))
                return 0


def write_to_file(seed, ETH_address, ETH_balance):
    # Write the seed, address, and balance to a file in the script's directory
    with open(wallets_file_path, "a") as f:
        log_message = f"Seed: {seed}\nAddress: {ETH_address}\nBalance: {ETH_balance} ETH\n\n"
        f.write(log_message)
        logging.info(f"Written to file: {log_message}")


def main():
    global wallets_scanned
    try:
        while True:
            seed = Bip39MnemonicGenerator().FromWordsNumber(12)
            ETH_address = bip44_ETH_wallet_from_seed(seed)
            etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
            if not etherscan_api_key:
                raise ValueError(
                    "The Etherscan API key must be set in the environment variables."
                )
            ETH_balance = check_ETH_balance(ETH_address, etherscan_api_key)

            logging.info(f"Seed: {seed}")
            logging.info(f"ETH address: {ETH_address}")
            logging.info(f"ETH balance: {ETH_balance} ETH")
            logging.info("")

            # Increment the counter
            wallets_scanned += 1

            # Check if the address has a balance
            if ETH_balance > 0:
                logging.info("(!) Wallet with balance found!")
                write_to_file(seed, ETH_address, ETH_balance)

    except KeyboardInterrupt:
        logging.info("Program interrupted by user. Exiting...")


if __name__ == "__main__":
    main()
