// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/proxy/Clones.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title TechneAgentFactory
 * @notice Factory for deploying TechneAgentAccount smart accounts
 * @dev Uses EIP-1167 minimal proxy pattern for gas-efficient deployments
 * 
 * Key Features:
 * - Deterministic addresses (CREATE2 via Clones)
 * - One account per user (enforced)
 * - Auto-whitelist common protocols on creation
 * - Gas-efficient: ~100K gas per deployment vs 2M for full contract
 */
contract TechneAgentFactory is Ownable {
    using Clones for address;

    // ============ State ============
    address public immutable implementation;
    
    // User -> Smart Account mapping
    mapping(address => address) public accountOf;
    
    // All deployed accounts (for iteration)
    address[] public allAccounts;
    
    // Default session key to add (Techne backend)
    address public defaultSessionKey;
    uint48 public defaultSessionKeyValidity = 365 days;
    uint256 public defaultDailyLimitUSD = 100_000 * 1e8; // $100K/day
    
    // Default protocols to whitelist
    address[] public defaultProtocols;
    bytes4[][] public defaultSelectors;

    // ============ Events ============
    event AccountCreated(
        address indexed owner,
        address indexed account,
        uint256 indexed index
    );
    event DefaultSessionKeySet(address indexed key, uint48 validity, uint256 dailyLimit);
    event DefaultProtocolsUpdated(uint256 count);

    // ============ Errors ============
    error AccountAlreadyExists();
    error InvalidOwner();
    error ZeroAddress();

    // ============ Constructor ============
    constructor(
        address _implementation,
        address _defaultSessionKey
    ) Ownable(msg.sender) {
        if (_implementation == address(0)) revert ZeroAddress();
        implementation = _implementation;
        defaultSessionKey = _defaultSessionKey;
    }

    // ============ Factory Functions ============

    /**
     * @notice Create a new smart account for a user
     * @param owner The owner of the new account (usually user's EOA)
     * @return account The deployed smart account address
     */
    function createAccount(address owner) external returns (address account) {
        if (owner == address(0)) revert InvalidOwner();
        if (accountOf[owner] != address(0)) revert AccountAlreadyExists();

        // Deploy deterministic clone
        bytes32 salt = keccak256(abi.encodePacked(owner));
        account = implementation.cloneDeterministic(salt);

        // Initialize the account
        ITechneAgentAccount(account).initialize(owner);

        // Add default session key if configured
        if (defaultSessionKey != address(0)) {
            ITechneAgentAccount(account).addSessionKey(
                defaultSessionKey,
                uint48(block.timestamp) + defaultSessionKeyValidity,
                defaultDailyLimitUSD
            );
        }

        // Whitelist default protocols
        if (defaultProtocols.length > 0) {
            ITechneAgentAccount(account).batchWhitelist(
                defaultProtocols,
                defaultSelectors
            );
        }

        // Register account
        accountOf[owner] = account;
        allAccounts.push(account);

        emit AccountCreated(owner, account, allAccounts.length - 1);
    }

    /**
     * @notice Get deterministic address for a user (without deploying)
     * @param owner The owner address
     * @return The counterfactual smart account address
     */
    function getAddress(address owner) external view returns (address) {
        bytes32 salt = keccak256(abi.encodePacked(owner));
        return implementation.predictDeterministicAddress(salt, address(this));
    }

    /**
     * @notice Check if account exists for user
     */
    function hasAccount(address owner) external view returns (bool) {
        return accountOf[owner] != address(0);
    }

    /**
     * @notice Get total number of accounts created
     */
    function totalAccounts() external view returns (uint256) {
        return allAccounts.length;
    }

    // ============ Admin Functions ============

    /**
     * @notice Set default session key for new accounts
     * @dev Only owner. Used to pre-configure Techne backend access.
     */
    function setDefaultSessionKey(
        address key,
        uint48 validity,
        uint256 dailyLimitUSD
    ) external onlyOwner {
        defaultSessionKey = key;
        defaultSessionKeyValidity = validity;
        defaultDailyLimitUSD = dailyLimitUSD;
        emit DefaultSessionKeySet(key, validity, dailyLimitUSD);
    }

    /**
     * @notice Set default protocols to whitelist for new accounts
     * @dev Only owner. Pre-configures Aave, Aerodrome, etc.
     */
    function setDefaultProtocols(
        address[] calldata protocols,
        bytes4[][] calldata selectors
    ) external onlyOwner {
        require(protocols.length == selectors.length, "Length mismatch");
        
        delete defaultProtocols;
        delete defaultSelectors;
        
        for (uint256 i = 0; i < protocols.length; i++) {
            defaultProtocols.push(protocols[i]);
            defaultSelectors.push(selectors[i]);
        }
        
        emit DefaultProtocolsUpdated(protocols.length);
    }

    /**
     * @notice Get all default protocols
     */
    function getDefaultProtocols() external view returns (
        address[] memory protocols,
        bytes4[][] memory selectors
    ) {
        return (defaultProtocols, defaultSelectors);
    }
}

// ============ Interface ============

interface ITechneAgentAccount {
    function initialize(address owner) external;
    function addSessionKey(address key, uint48 validUntil, uint256 dailyLimitUSD) external;
    function batchWhitelist(address[] calldata protocols, bytes4[][] calldata selectors) external;
}
