const { ethers } = require("hardhat");

async function main() {
    // Check nonce 80 which shows as [CONTRACT]
    const factoryAddr = "0x33f5e2F6d194869ACc60C965C2A24eDC5de8a216";

    console.log("Checking contract at:", factoryAddr);

    try {
        const Factory = await ethers.getContractAt("TechneAccountFactory", factoryAddr);
        const impl = await Factory.implementation();
        console.log("SUCCESS! This is the TechneAccountFactory!");
        console.log("  Factory Address:", factoryAddr);
        console.log("  Implementation Address:", impl);

        // Get some more info
        const deployer = "0xa30A689ec0F9D717C5bA1098455B031b868B720f";
        const accounts = await Factory.getAccountCount(deployer);
        console.log("  Deployer accounts:", accounts.toString());
    } catch (e) {
        console.log("Not the factory:", e.message);

        // Try checking if it's TechneAgentAccount implementation
        try {
            const Account = await ethers.getContractAt("TechneAgentAccount", factoryAddr);
            const owner = await Account.owner();
            console.log("This might be TechneAgentAccount, owner:", owner);
        } catch (e2) {
            console.log("Also not TechneAgentAccount:", e2.message.slice(0, 100));
        }
    }
}

main().catch(console.error);
