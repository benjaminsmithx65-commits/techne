const { ethers } = require("hardhat");

async function main() {
    console.log("=== Deploying TechneAccountFactory ===\n");

    const [deployer] = await ethers.getSigners();
    console.log("Deployer:", deployer.address);

    const balance = await ethers.provider.getBalance(deployer.address);
    console.log("Balance:", ethers.formatEther(balance), "ETH\n");

    // Deploy Factory (which creates implementation in constructor)
    console.log("Deploying TechneAccountFactory...");
    const Factory = await ethers.getContractFactory("TechneAccountFactory");
    const factory = await Factory.deploy({
        gasLimit: 5000000
    });

    // Wait for deployment transaction to be mined
    console.log("Waiting for deployment confirmation...");
    const deployTx = factory.deploymentTransaction();
    await deployTx.wait(2); // Wait for 2 confirmations

    const factoryAddress = await factory.getAddress();
    console.log("Factory deployed to:", factoryAddress);

    // Now get implementation address
    const implementationAddress = await factory.implementation();

    console.log("\n=== Deployment Complete ===");
    console.log("Factory Address:", factoryAddress);
    console.log("Implementation Address:", implementationAddress);

    // Verify bytecode exists
    const factoryCode = await ethers.provider.getCode(factoryAddress);
    const implCode = await ethers.provider.getCode(implementationAddress);
    console.log("\nFactory bytecode length:", factoryCode.length);
    console.log("Implementation bytecode length:", implCode.length);

    console.log("\n=== Next Steps ===");
    console.log("1. Update frontend with factory address");
    console.log("2. Users can create Smart Accounts via factory.createAccount(salt)");
    console.log("3. Backend needs session key added to each user's account");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
