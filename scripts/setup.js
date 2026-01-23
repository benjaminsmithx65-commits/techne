const { ethers } = require("hardhat");

async function main() {
    console.log("Configuring TechneAgentWalletV43...");

    const [deployer] = await ethers.getSigners();
    console.log("Using address:", deployer.address);

    // New contract address
    const CONTRACT_ADDRESS = "0xC01F88CcC5Ee12DE6899df6bAcC0EE83C55960847";
    const AAVE_POOL = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5";
    const USER_ADDRESS = "0xbA9D6947C0aD6eA2AaA99507355cf83B4D098058";

    // ABI for configuration functions
    const ABI = [
        "function setProtocolApproval(address protocol, bool approved) external",
        "function setLendingProtocol(address protocol, bool isLending) external",
        "function setUserWhitelist(address user, bool whitelisted) external",
        "function grantRole(bytes32 role, address account) external",
        "function AGENT_ROLE() external view returns (bytes32)",
        "function approvedProtocols(address) external view returns (bool)",
        "function isLendingProtocol(address) external view returns (bool)",
        "function whitelist(address) external view returns (bool)"
    ];

    const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, deployer);

    console.log("\n1. Approving AAVE pool as protocol...");
    let tx = await contract.setProtocolApproval(AAVE_POOL, true);
    await tx.wait();
    console.log("   ✅ Approved");

    console.log("\n2. Setting AAVE as lending protocol...");
    tx = await contract.setLendingProtocol(AAVE_POOL, true);
    await tx.wait();
    console.log("   ✅ Set as lending protocol");

    console.log("\n3. Whitelisting user...");
    tx = await contract.setUserWhitelist(USER_ADDRESS, true);
    await tx.wait();
    console.log("   ✅ User whitelisted");

    // Verify
    console.log("\n--- Verification ---");
    console.log("approvedProtocols(AAVE):", await contract.approvedProtocols(AAVE_POOL));
    console.log("isLendingProtocol(AAVE):", await contract.isLendingProtocol(AAVE_POOL));
    console.log("whitelist(USER):", await contract.whitelist(USER_ADDRESS));

    console.log("\n✅ Configuration complete!");
    console.log("Contract is ready for use at:", CONTRACT_ADDRESS);
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
