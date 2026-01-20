// Whitelist user on TechneAgentWalletV3
import 'dotenv/config';
import { createWalletClient, http, createPublicClient } from "viem";
import { base } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";

const V3_ADDRESS = "0xc590baaf11cd64c5477181950a98a7e4dcc78c88";
const USER_TO_WHITELIST = "0xbA9D6947C0aD6eA2AaA99507355cf83B4D098058";

const ABI = [
    {
        "inputs": [{ "name": "user", "type": "address" }],
        "name": "whitelistUser",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{ "name": "user", "type": "address" }],
        "name": "isWhitelisted",
        "outputs": [{ "type": "bool" }],
        "stateMutability": "view",
        "type": "function"
    }
];

async function main() {
    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) {
        throw new Error("PRIVATE_KEY not set");
    }

    const account = privateKeyToAccount(privateKey);
    console.log("Admin:", account.address);

    const publicClient = createPublicClient({
        chain: base,
        transport: http("https://mainnet.base.org")
    });

    const walletClient = createWalletClient({
        account,
        chain: base,
        transport: http("https://mainnet.base.org")
    });

    console.log("Whitelisting:", USER_TO_WHITELIST);

    const hash = await walletClient.writeContract({
        address: V3_ADDRESS,
        abi: ABI,
        functionName: "whitelistUser",
        args: [USER_TO_WHITELIST]
    });

    console.log("TX:", hash);
    console.log("Waiting for confirmation...");

    await publicClient.waitForTransactionReceipt({ hash });

    // Verify
    const isWhitelisted = await publicClient.readContract({
        address: V3_ADDRESS,
        abi: ABI,
        functionName: "isWhitelisted",
        args: [USER_TO_WHITELIST]
    });

    console.log("✅ User whitelisted:", isWhitelisted);
}

main().catch(console.error);
