// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/proxy/Clones.sol";
import "./TechneAgentAccount.sol";

/**
 * @title TechneAccountFactory
 * @notice Factory for deploying TechneAgentAccount instances
 * @dev Uses minimal proxies (EIP-1167) for gas-efficient deployments
 */
contract TechneAccountFactory {
    using Clones for address;

    // ============ State ============
    address public immutable implementation;
    
    // Track deployed accounts
    mapping(address => address[]) public userAccounts;
    mapping(address => bool) public isAccount;

    // ============ Events ============
    event AccountCreated(
        address indexed owner,
        address indexed account,
        bytes32 salt
    );

    // ============ Constructor ============
    constructor() {
        implementation = address(new TechneAgentAccount());
    }

    // ============ Factory Functions ============

    /**
     * @notice Create a new agent account for the caller
     * @param salt Unique salt for deterministic address
     * @return account The created account address
     */
    function createAccount(bytes32 salt) external returns (address account) {
        // Combine caller address with salt for uniqueness
        bytes32 combinedSalt = keccak256(abi.encodePacked(msg.sender, salt));
        
        account = implementation.cloneDeterministic(combinedSalt);
        TechneAgentAccount(payable(account)).initialize(msg.sender);
        
        userAccounts[msg.sender].push(account);
        isAccount[account] = true;
        
        emit AccountCreated(msg.sender, account, salt);
    }

    /**
     * @notice Predict the address of an account before deployment
     * @param owner The owner address
     * @param salt The salt used for deployment
     */
    function getAddress(address owner, bytes32 salt) external view returns (address) {
        bytes32 combinedSalt = keccak256(abi.encodePacked(owner, salt));
        return implementation.predictDeterministicAddress(combinedSalt);
    }

    /**
     * @notice Get all accounts for a user
     */
    function getAccounts(address owner) external view returns (address[] memory) {
        return userAccounts[owner];
    }

    /**
     * @notice Get the number of accounts for a user
     */
    function getAccountCount(address owner) external view returns (uint256) {
        return userAccounts[owner].length;
    }
}
