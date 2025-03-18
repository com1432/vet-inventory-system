# Remove existing Git setup
rm -rf .git

# Initialize new Git repository
git init

# Set Git identity
git config --global user.email "comscie1432@email"
git config --global user.name "com1432"

# Configure for large files
git config --global http.postBuffer 524288000
git config --global http.maxRequestBuffer 100M
git config --global core.compression 9

# Configure credential helper
git config --global credential.helper store

# Add files in smaller chunks
git add "*.py"
git commit -m "Add Python files"

git add "*.json"
git commit -m "Add JSON files"

git add .
git commit -m "Add remaining files"

# Create main branch
git branch -M main

# Add remote repository
git remote add origin https://github.com/com1432/vet-inventory-system.git

# Push to main branch with increased buffer
git push --set-upstream origin main
