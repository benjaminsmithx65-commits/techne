// Deploy TechneAgentWalletV2 - Institutional Grade
// Run: npx hardhat run scripts/deploy-v2.js --network base

import hre from "hardhat";
import fs from "fs";
import { createWalletClient, http, createPublicClient, encodeDeployData } from "viem";
import { base } from "viem/chains";
import { privateKeyToAccount } from "viem/accounts";

async function main() {
    console.log("🚀 Deploying TechneAgentWalletV2...\n");

    // Get private key from env
    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) {
        throw new Error("PRIVATE_KEY not set in .env");
    }

    // Create account
    const account = privateKeyToAccount(privateKey);
    console.log("Deployer:", account.address);

    // Create clients
    const rpcUrl = process.env.ALCHEMY_RPC_URL || "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb";

    const publicClient = createPublicClient({
        chain: base,
        transport: http(rpcUrl)
    });

    const walletClient = createWalletClient({
        account,
        chain: base,
        transport: http(rpcUrl)
    });

    // Get balance
    const balance = await publicClient.getBalance({ address: account.address });
    console.log("Balance:", (Number(balance) / 1e18).toFixed(4), "ETH\n");

    // ============================================
    // CONFIGURATION
    // ============================================

    const config = {
        USDC: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        AERODROME_ROUTER: "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
        AERODROME_FACTORY: "0x420DD381b31aEf6683db6B902084cB0FFECe40Da",
        USDC_PRICE_FEED: "0x7e860098F58bBFC8648a4311b374B1D669a2bc6B",
        AGENT: account.address,
        SIGNERS: [
            "0xa30a689ec0f9d717c5ba1098455b031b868b720f",
            "0x58e66a7a6883ef761e6adb0f08b0d94f70343eb6",
            "0x9cf94969639d0905a6cb617925f06052643cce04"
        ]
    };

    console.log("📋 Configuration:");
    console.log("  USDC:", config.USDC);
    console.log("  Agent:", config.AGENT);
    console.log("  Signers:", config.SIGNERS.length, "addresses\n");

    // ============================================
    // DEPLOY
    // ============================================

    console.log("⏳ Deploying contract...");

    // Get artifact
    const artifact = await hre.artifacts.readArtifact("TechneAgentWalletV2");

    // Encode deploy data
    const deployData = encodeDeployData({
        abi: artifact.abi,
        bytecode: artifact.bytecode,
        args: [
            config.USDC,
            config.AERODROME_ROUTER,
            config.AERODROME_FACTORY,
            config.AGENT,
            config.USDC_PRICE_FEED,
            config.SIGNERS
        ]
    });

    // Estimate gas
    const gasEstimate = await publicClient.estimateGas({
        account: account.address,
        data: deployData
    });
    console.log("  Gas estimate:", gasEstimate.toString());

    // Deploy
    const hash = await walletClient.sendTransaction({
        data: deployData,
        gas: gasEstimate + 100000n // Add buffer
    });

    console.log("\n📤 TX sent:", hash);
    console.log("⏳ Waiting for confirmation...");

    // Wait for receipt
    const receipt = await publicClient.waitForTransactionReceipt({ hash });

    const contractAddress = receipt.contractAddress;

    console.log("\n✅ TechneAgentWalletV2 deployed!");
    console.log("📍 Contract Address:", contractAddress);
    console.log("🔗 Basescan: https://basescan.org/address/" + contractAddress);

    // ============================================
    // SUMMARY
    // ============================================

    console.log("\n" + "=".repeat(60));
    console.log("🎉 DEPLOYMENT COMPLETE");
    console.log("=".repeat(60));
    console.log("\n⚡ Contract Address:", contractAddress);
    console.log("\nUpdate these files:");
    console.log("  1. frontend/agent-wallet-ui.js → contractAddress");
    console.log("  2. backend/config/contracts.py → AGENT_WALLET_V2_ADDRESS");
    console.log("\nSecurity:");
    console.log("  ✅ 2-day timelock | ✅ Multi-sig 2/3");
    console.log("  ✅ $1M daily limit | ✅ Circuit breaker");

    // Save
    const deploymentInfo = {
        network: "base",
        contract: "TechneAgentWalletV2",
        address: contractAddress,
        deployer: account.address,
        txHash: hash,
        timestamp: new Date().toISOString(),
        signers: config.SIGNERS
    };

    fs.writeFileSync(
        "deployments/base-v2.json",
        JSON.stringify(deploymentInfo, null, 2)
    );
    console.log("\n📁 Saved to: deployments/base-v2.json");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error("❌ Deployment failed:", error);
        process.exit(1);
    });
