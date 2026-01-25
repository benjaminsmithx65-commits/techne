---
description: AI developer rules for Techne Finance - enforces vertical slice implementation
---

# AI DEVELOPER CONSTITUTION
# PROJECT: Techne Finance (DeFi Builder)

## 1. THE "VERTICAL SLICE" RULE (CRITICAL)
You are strictly forbidden from implementing Frontend features without implementing the corresponding Backend Logic/Rules.
When I ask for a new setting/feature, you must execute these 4 steps IN ORDER:

1. **[DATA]** Update the Database Schema / Structs / Config types.
2. **[LOGIC]** Update the RULES ENGINE (Guardian/Strategy Logic) to USE the new variable in an `if/else` check.
   - WARNING: Merely adding the variable to the config object is a FAILURE. You must write logic that enforces it.
3. **[API]** Update the Interface/API layer to pass the data.
4. **[UI]** Only then, create the Frontend Input/Slider.

### Implementation Checklist:
```
[ ] 1. DATA - Schema/struct updated
[ ] 2. LOGIC - Rules engine uses the value (if/else check exists)
[ ] 3. API - Endpoint passes the data correctly
[ ] 4. UI - Frontend input created
```

## 2. STYLE & CONSISTENCY
- **MIMIC EXISTING CODE**: Read the surrounding code first. Match the indentation, variable naming, and error handling patterns exactly.
- **NO HALLUCINATIONS**: Do not import libraries that are not in `package.json` / `requirements.txt` unless explicitly asked.

## 3. SECURITY (DeFi Context)
- Every user input from the Frontend is considered **"Malicious"** until validated by the Backend Rules Engine.
- Never rely on Frontend validation alone.
- All financial amounts must be validated on-chain or in the rules engine.

## 4. ERROR CORRECTION PRIORITY
If the user points out a bug (e.g., "The limit isn't working"):
1. **FIRST**: Check the RULES ENGINE (Step 2) - the logic gates
2. **SECOND**: Check the API layer
3. **LAST**: Check the UI

Assume the issue is in the **LOGIC**, not the UI.

## 5. KEY FILES FOR TECHNE

### Backend Rules Engine:
- `backend/agents/contract_monitor.py` - Main allocation logic, protocol selection
- `backend/agents/strategy_executor.py` - Strategy execution
- `backend/api/agent_router.py` - API endpoints for agent operations

### Frontend:
- `frontend/portfolio.js` - Portfolio dashboard
- `frontend/build.js` - Agent builder UI

### Contract:
- TechneAgentWallet V4.3.3: `0x323f98c4e05073c2f76666944d95e39b78024efd`
- TechneAccountFactory: `0x33f5e2F6d194869ACc60C965C2A24eDC5de8a216`

## 6. TURBO MODE (AUTO-APPROVE ALL)

When user says "turbo", "/turbo", or "bez approva":
// turbo-all

### Auto-Approve Commands:
// turbo
- `npm install`, `npm run dev`, `npm run build`, `npm test`
// turbo
- `python`, `pip install`, `uvicorn`, `pytest`
// turbo
- `npx hardhat compile`, `npx hardhat run`, `npx hardhat test`
// turbo
- `git add`, `git commit`, `git push`, `git pull`
// turbo
- `curl`, `Invoke-RestMethod`
// turbo
- File create/edit/delete within project directories

### Never Auto-Approve (require explicit confirmation):
- Deleting system files outside project
- Running unknown scripts from internet
- Transactions involving real money (mainnet deploys with funds)

### Turbo Behavior:
1. Set `SafeToAutoRun: true` for all listed command types
2. Set `ShouldAutoProceed: true` for notify_user when confident
3. Continue working without waiting for user between steps
4. Only stop on unrecoverable errors

## 7. FULL STACK INTEGRATION RULE (CRITICAL)

**NEVER implement features in isolation.** Every feature must work END-TO-END.

### The "Connected Systems" Checklist:
Before marking ANY feature as "done", verify ALL connections:

```
[ ] 1. CONTRACT - Does the smart contract have the required function?
       - If NO: Either add it OR find existing function that works
       - WARNING: Don't add UI for features contract can't execute!

[ ] 2. BACKEND - Is there an endpoint that:
       - Receives the frontend request?
       - Calls the contract/service correctly?
       - Returns data in the format frontend expects?

[ ] 3. FRONTEND - Does the UI:
       - Call the correct backend endpoint?
       - Use the correct HTTP method (GET/POST)?
       - Handle the response data structure properly?
       - Match existing styling patterns?

[ ] 4. DATA FLOW - Trace the complete path:
       Frontend Button → API Call → Backend Handler → Service Logic → Contract/DB → Response
```

### Anti-Patterns (FORBIDDEN):
1. ❌ Adding UI slider without backend using that value
2. ❌ Creating backend endpoint without frontend calling it
3. ❌ Adding contract function without backend/frontend integration
4. ❌ Using hardcoded values instead of actual API calls
5. ❌ Creating new CSS classes without matching existing theme
6. ❌ Adding console.log("TODO") and leaving it

### Before Implementing, ALWAYS Ask:
1. "Where does this data come FROM?" (user input, contract, API?)
2. "Where does this data GO?" (contract, DB, display?)
3. "What existing code handles similar features?" (copy pattern)
4. "Is there an existing endpoint I can extend vs. creating new?"

### Style Consistency Rules:
- **CSS**: Use existing variables from `styles.css` (--color-*, --radius-*, etc.)
- **JS**: Match existing function naming patterns (camelCase, async/await style)
- **Python**: Match existing FastAPI patterns (router structure, Pydantic models)
- **Error handling**: Copy error patterns from similar existing code

### When Adding NEW Functionality:
1. FIRST: Search for similar existing implementation
2. SECOND: Understand the full data flow of that similar feature
3. THIRD: Implement your feature following that exact same pattern
4. FOURTH: Test by tracing the complete path manually

## 8. DEBUGGING PRIORITY ORDER

When user reports "X doesn't work":

1. **Console errors** - Check browser DevTools for JS errors
2. **Network tab** - Check if API call is made and what response is
3. **Backend logs** - Check uvicorn output for Python errors
4. **Contract state** - Verify contract has correct data/permissions
5. **Frontend logic** - Only then check UI event handlers

### Common Issues Checklist:
```
[ ] Wrong API URL (localhost vs production)
[ ] Missing CORS headers
[ ] Wrong HTTP method (GET vs POST)
[ ] Data format mismatch (JSON structure)
[ ] BigInt/Number mixing in JS
[ ] Missing window. prefix for globals
[ ] Contract function not in ABI
[ ] Wallet not connected
```
