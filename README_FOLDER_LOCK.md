# Folder Structure Lock

This repo maintains a **top-level folder structure contract** to prevent accidental renames/removals/additions.

## Contract
Allowed top-level folders:
- `agent/`
- `backend/`
- `frontend/`

## Lock manifest
- `FOLDER_STRUCTURE.lock.json`

## How it is enforced
- `lock_folder_structure.py` (Python) and `lock_folder_structure_node.mjs` (Node) validate current top-level directories against `FOLDER_STRUCTURE.lock.json`.

If the contract is violated, the scripts exit with a non-zero status code.

## Usage
### Python
```bash
python lock_folder_structure.py
```

### Node
```bash
node lock_folder_structure_node.mjs
```

## CI / Hooks
To make this stricter, wire the scripts into your CI pipeline or pre-commit hooks.

## Notes
- This repo-level lock **does not attempt** to make folders immutable on disk (Windows ACL changes are brittle and can break developer workflows).
- Update `FOLDER_STRUCTURE.lock.json` intentionally if the repo structure is meant to change.

