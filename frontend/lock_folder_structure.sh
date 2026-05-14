@echo off
REM Runs folder structure lock guard from repo root.
REM Usage: frontend\lock_folder_structure.sh
cd /d "%~dp0.."\
node lock_folder_structure_node.mjs

