/**
 * Deploy TechneAgentWalletV43 (V4.3.2) to Base Mainnet using viem
 * 
 * Run: node scripts/deploy-v43-viem.mjs
 */

import { createWalletClient, createPublicClient, http, parseAbi } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base } from 'viem/chains';
import fs from 'fs';
import 'dotenv/config';

// Base Mainnet Addresses
const ADDRESSES = {
    USDC: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    WETH: "0x4200000000000000000000000000000000000006",
    ETH_USD_ORACLE: "0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70",
    SEQUENCER_UPTIME: "0xBCF85224fc0756B9Fa45aA7892530B47e10b6433",
    AAVE_POOL: "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
    AERODROME_ROUTER: "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
    AERODROME_FACTORY: "0x420DD381b31aEf6683db6B902084cB0FFECe40Da",
};

async function main() {
    // Load compiled artifact
    const artifact = JSON.parse(
        fs.readFileSync('./artifacts/contracts/TechneAgentWalletV43.sol/TechneAgentWalletV43.json', 'utf8')
    );

    // Setup viem clients
    if (!process.env.PRIVATE_KEY) {
        throw new Error("PRIVATE_KEY not set in .env file");
    }
    const pk = process.env.PRIVATE_KEY.startsWith('0x')
        ? process.env.PRIVATE_KEY
        : `0x${process.env.PRIVATE_KEY}`;
    const account = privateKeyToAccount(pk);

    const publicClient = createPublicClient({
        chain: base,
        transport: http(process.env.ALCHEMY_RPC_URL || "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb")
    });

    const walletClient = createWalletClient({
        account,
        chain: base,
        transport: http(process.env.ALCHEMY_RPC_URL || "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb")
    });

    console.log("🚀 Deploying TechneAgentWalletV43 to Base Mainnet");
    console.log("================================================");
    console.log("Deployer:", account.address);

    const balance = await publicClient.getBalance({ address: account.address });
    console.log("Balance:", Number(balance) / 1e18, "ETH");
    console.log("");

    console.log("📋 Constructor Parameters:");
    console.log("  USDC:", ADDRESSES.USDC);
    console.log("  WETH:", ADDRESSES.WETH);
    console.log("  Admin:", account.address);
    console.log("  Agent:", account.address);
    console.log("  Guardian:", account.address);
    console.log("  Price Oracle:", ADDRESSES.ETH_USD_ORACLE);
    console.log("  Sequencer Feed:", ADDRESSES.SEQUENCER_UPTIME);
    console.log("  Aave Pool:", ADDRESSES.AAVE_POOL);
    console.log("  DEX Router:", ADDRESSES.AERODROME_ROUTER);
    console.log("  DEX Factory:", ADDRESSES.AERODROME_FACTORY);
    console.log("");

    console.log("⏳ Deploying...");

    // Encode constructor args
    const { encodeDeployData } = await import('viem');

    const deployData = encodeDeployData({
        abi: artifact.abi,
        bytecode: artifact.bytecode,
        args: [
            ADDRESSES.USDC,
            ADDRESSES.WETH,
            account.address,  // admin
            account.address,  // agent
            account.address,  // guardian
            ADDRESSES.ETH_USD_ORACLE,
            ADDRESSES.SEQUENCER_UPTIME,
            ADDRESSES.AAVE_POOL,
            ADDRESSES.AERODROME_ROUTER,
            ADDRESSES.AERODROME_FACTORY
        ]
    });

    // Send deployment transaction
    const hash = await walletClient.sendTransaction({
        data: deployData,
    });

    console.log("📤 TX Hash:", hash);
    console.log("⏳ Waiting for confirmation...");

    // Wait for receipt
    const receipt = await publicClient.waitForTransactionReceipt({ hash });

    console.log("");
    console.log("✅ TechneAgentWalletV43 Deployed!");
    console.log("================================");
    console.log("📍 Contract Address:", receipt.contractAddress);
    console.log("⛽ Gas Used:", receipt.gasUsed.toString());
    console.log("");

    // Save deployment info
    const deployment = {
        version: "V4.3.2",
        address: receipt.contractAddress,
        deployer: account.address,
        txHash: hash,
        network: "base",
        chainId: 8453,
        timestamp: new Date().toISOString(),
        gasUsed: receipt.gasUsed.toString(),
        constructor: {
            usdc: ADDRESSES.USDC,
            weth: ADDRESSES.WETH,
            admin: account.address,
            agent: account.address,
            guardian: account.address,
            priceOracle: ADDRESSES.ETH_USD_ORACLE,
            sequencerFeed: ADDRESSES.SEQUENCER_UPTIME,
            aavePool: ADDRESSES.AAVE_POOL,
            dexRouter: ADDRESSES.AERODROME_ROUTER,
            dexFactory: ADDRESSES.AERODROME_FACTORY
        },
        features: [
            "Flash Loan Deleverage",
            "Cross-Asset Swap (multi-hop)",
            "L2 Sequencer Check",
            "Health Factor Monitoring",
            "Rebalance Hysteresis (4h cooldown)",
            "Fee-on-Transfer Safe",
            "Signature Replay Protection"
        ]
    };

    fs.writeFileSync(
        "deployments/v43-base-mainnet.json",
        JSON.stringify(deployment, null, 2)
    );

    console.log("📁 Deployment saved to deployments/v43-base-mainnet.json");
    console.log("");
    console.log("🔧 Next steps:");
    console.log("  1. Verify on Basescan");
    console.log("  2. Whitelist users");
    console.log("  3. Approve protocols (Aave, Moonwell, etc.)");
    console.log("  4. Transfer AGENT_ROLE to backend signer");
    console.log("  5. Transfer DEFAULT_ADMIN_ROLE to Gnosis Safe");
}

main().catch(console.error);
