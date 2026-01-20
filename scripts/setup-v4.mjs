// Setup V4: Whitelist user + Approve protocols
import 'dotenv/config';
import { createWalletClient, http, createPublicClient } from "viem";
import { base } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";

const V4_ADDRESS = "0x360455d8c1bfee9d471d69026eed972997714903";
const USER_TO_WHITELIST = "0xbA9D6947C0aD6eA2AaA99507355cf83B4D098058";

// Protocols to approve
const PROTOCOLS = {
    AAVE_V3: "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
    COMPOUND_V3: "0x46e6b214b524310239732D51387075E0e70970bf",
    MOONWELL: "0xfBb21d0380bEE3312B33c4353c8936a0F13EF26C",
    MORPHO: "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
};

const ABI = [
    {
        "inputs": [{ "name": "user", "type": "address" }],
        "name": "whitelistUser",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            { "name": "protocol", "type": "address" },
            { "name": "approved", "type": "bool" }
        ],
        "name": "approveProtocol",
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
    },
    {
        "inputs": [{ "name": "protocol", "type": "address" }],
        "name": "approvedProtocols",
        "outputs": [{ "type": "bool" }],
        "stateMutability": "view",
        "type": "function"
    }
];

async function main() {
    console.log("🔧 Setting up TechneAgentWalletV4...\n");

    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) throw new Error("PRIVATE_KEY not set");

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

    // 1. Whitelist user
    console.log("\n⏳ Whitelisting user:", USER_TO_WHITELIST);
    const tx1 = await walletClient.writeContract({
        address: V4_ADDRESS,
        abi: ABI,
        functionName: "whitelistUser",
        args: [USER_TO_WHITELIST]
    });
    console.log("TX:", tx1);
    await publicClient.waitForTransactionReceipt({ hash: tx1 });
    console.log("✅ User whitelisted!");

    // 2. Approve protocols
    for (const [name, addr] of Object.entries(PROTOCOLS)) {
        console.log(`\n⏳ Approving ${name}:`, addr);
        const tx = await walletClient.writeContract({
            address: V4_ADDRESS,
            abi: ABI,
            functionName: "approveProtocol",
            args: [addr, true]
        });
        console.log("TX:", tx);
        await publicClient.waitForTransactionReceipt({ hash: tx });
        console.log(`✅ ${name} approved!`);
    }

    // 3. Verify
    console.log("\n📋 Verification:");
    const isWhitelisted = await publicClient.readContract({
        address: V4_ADDRESS,
        abi: ABI,
        functionName: "isWhitelisted",
        args: [USER_TO_WHITELIST]
    });
    console.log("  User whitelisted:", isWhitelisted);

    for (const [name, addr] of Object.entries(PROTOCOLS)) {
        const approved = await publicClient.readContract({
            address: V4_ADDRESS,
            abi: ABI,
            functionName: "approvedProtocols",
            args: [addr]
        });
        console.log(`  ${name} approved:`, approved);
    }

    console.log("\n🎉 V4 Setup Complete!");
}

main().catch(console.error);
