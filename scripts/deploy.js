const { ethers } = require("hardhat");

async function main() {
    console.log("Deploying TechneAgentWalletV43 with exitPosition()...");

    const [deployer] = await ethers.getSigners();
    console.log("Deployer address:", deployer.address);
    console.log("Balance:", ethers.formatEther(await ethers.provider.getBalance(deployer.address)), "ETH");

    // Constructor parameters for Base mainnet
    const constructorArgs = [
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  // USDC
        "0x4200000000000000000000000000000000000006",  // WETH
        deployer.address,                              // Admin
        deployer.address,                              // Agent
        deployer.address,                              // Guardian
        "0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70",  // Price Oracle
        "0xBCF85224fc0756B9Fa45aA7892530B47e10b6433",  // Sequencer Feed
        "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",  // Aave Pool
        "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",  // DEX Router (Aerodrome)
        "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"   // Aero Factory
    ];

    console.log("\nConstructor args:", constructorArgs);

    // Deploy
    const TechneWallet = await ethers.getContractFactory("TechneAgentWalletV43");
    const wallet = await TechneWallet.deploy(...constructorArgs);

    await wallet.waitForDeployment();
    const address = await wallet.getAddress();

    console.log("\n✅ TechneAgentWalletV43 deployed to:", address);
    console.log("\nNext steps:");
    console.log("1. Update backend TECHNE_WALLET address to:", address);
    console.log("2. Whitelist user address");
    console.log("3. Approve AAVE Pool as lending protocol");
    console.log("4. Migrate funds from old contract if needed");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
