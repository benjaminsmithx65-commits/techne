const { ethers } = require("hardhat");

async function main() {
    const deployer = "0xa30A689ec0F9D717C5bA1098455B031b868B720f";

    console.log("Checking deployer:", deployer);
    const nonce = await ethers.provider.getTransactionCount(deployer);
    console.log("Current nonce:", nonce);

    console.log("\nChecking recent contract addresses:");
    for (let n = 60; n < nonce; n++) {
        // ethers v6: getCreateAddress
        const addr = ethers.getCreateAddress({ from: deployer, nonce: n });
        const code = await ethers.provider.getCode(addr);
        const hasCode = code.length > 2;
        console.log(`  Nonce ${n}: ${addr} ${hasCode ? '[CONTRACT]' : '[EOA]'}`);
    }

    // Check nonce 61 and 62 specifically (likely factory)
    console.log("\n=== Most Likely Factory Addresses ===");
    for (let n = 61; n <= 62; n++) {
        const addr = ethers.getCreateAddress({ from: deployer, nonce: n });
        console.log(`Nonce ${n}: ${addr}`);

        try {
            const Factory = await ethers.getContractAt("TechneAccountFactory", addr);
            const impl = await Factory.implementation();
            console.log(`  -> This is the FACTORY! Implementation: ${impl}`);
        } catch (e) {
            console.log(`  -> Not the factory (${e.message.slice(0, 50)}...)`);
        }
    }
}

main().catch(console.error);
