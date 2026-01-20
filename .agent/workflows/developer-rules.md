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
