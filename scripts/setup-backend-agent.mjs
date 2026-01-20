// Generate a new wallet for backend agent and grant AGENT role
import 'dotenv/config';
import { createWalletClient, http, createPublicClient } from "viem";
import { base } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";
import { randomBytes } from "crypto";
import fs from "fs";

const V3_ADDRESS = "0xc590baaf11cd64c5477181950a98a7e4dcc78c88";

// Generate private key using crypto
function generatePrivateKey() {
    return '0x' + randomBytes(32).toString('hex');
}

// AGENT_ROLE = keccak256("AGENT_ROLE")
const AGENT_ROLE = "0x7a05a596cb0ce7fdea8a1e1ec73be300bdb35097c944ce1897202f7a13122eb2";

const ABI = [
    {
        "inputs": [
            { "name": "role", "type": "bytes32" },
            { "name": "account", "type": "address" }
        ],
        "name": "grantRole",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            { "name": "role", "type": "bytes32" },
            { "name": "account", "type": "address" }
        ],
        "name": "hasRole",
        "outputs": [{ "type": "bool" }],
        "stateMutability": "view",
        "type": "function"
    }
];

async function main() {
    console.log("🔐 Setting up Backend Agent Wallet...\n");

    // 1. Generate new wallet
    const newPrivateKey = generatePrivateKey();
    const newAccount = privateKeyToAccount(newPrivateKey);
    const newAddress = newAccount.address;

    console.log("✅ Generated new wallet:");
    console.log("   Address:", newAddress);
    console.log("   Private Key:", newPrivateKey);
    console.log("");

    // 2. Connect with admin to grant role
    const adminPrivateKey = process.env.PRIVATE_KEY;
    if (!adminPrivateKey) {
        throw new Error("PRIVATE_KEY not set - need admin to grant role");
    }

    const adminAccount = privateKeyToAccount(adminPrivateKey);
    console.log("👤 Admin:", adminAccount.address);

    const publicClient = createPublicClient({
        chain: base,
        transport: http("https://mainnet.base.org")
    });

    const walletClient = createWalletClient({
        account: adminAccount,
        chain: base,
        transport: http("https://mainnet.base.org")
    });

    // 3. Grant AGENT_ROLE to new wallet
    console.log("\n⏳ Granting AGENT_ROLE to backend wallet...");

    const hash = await walletClient.writeContract({
        address: V3_ADDRESS,
        abi: ABI,
        functionName: "grantRole",
        args: [AGENT_ROLE, newAddress]
    });

    console.log("TX:", hash);
    console.log("Waiting for confirmation...");

    await publicClient.waitForTransactionReceipt({ hash });

    // 4. Verify
    const hasRole = await publicClient.readContract({
        address: V3_ADDRESS,
        abi: ABI,
        functionName: "hasRole",
        args: [AGENT_ROLE, newAddress]
    });

    console.log("\n✅ AGENT_ROLE granted:", hasRole);

    // 5. Save to backend/.env
    const envPath = "backend/.env";
    let envContent = "";

    if (fs.existsSync(envPath)) {
        envContent = fs.readFileSync(envPath, "utf8");
    }

    // Add or update AGENT_PRIVATE_KEY
    if (envContent.includes("AGENT_PRIVATE_KEY=")) {
        envContent = envContent.replace(/AGENT_PRIVATE_KEY=.*/g, `AGENT_PRIVATE_KEY=${newPrivateKey}`);
    } else {
        envContent += `\n# Backend Agent Wallet (auto-generated)\nAGENT_PRIVATE_KEY=${newPrivateKey}\nAGENT_ADDRESS=${newAddress}\n`;
    }

    fs.writeFileSync(envPath, envContent);

    console.log("\n📁 Saved to backend/.env");
    console.log("\n" + "=".repeat(60));
    console.log("🎉 BACKEND AGENT WALLET CONFIGURED!");
    console.log("=".repeat(60));
    console.log("\n📋 Summary:");
    console.log("   Agent Address:", newAddress);
    console.log("   Has AGENT_ROLE:", hasRole);
    console.log("   Private key saved to: backend/.env");
    console.log("\n⚠️  IMPORTANT: Fund this address with ~0.01 ETH for gas!");
    console.log("   Deposit ETH to:", newAddress);
}

main().catch(console.error);
