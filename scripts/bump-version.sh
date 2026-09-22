#!/bin/bash
# Ändert die einzige kanonische Versionsquelle in euercli/__init__.py.
set -e

BUMP_TYPE=$1
if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo "Usage: $0 {major|minor|patch}"
    exit 1
fi

# Get current version from euercli/__init__.py
CURRENT_VERSION=$(sed -nE 's/^VERSION = "([0-9]+\.[0-9]+\.[0-9]+)"$/\1/p' euercli/__init__.py | head -n 1)
if [ -z "$CURRENT_VERSION" ]; then
    echo "Error: Could not find canonical VERSION in euercli/__init__.py"
    exit 1
fi
echo "Current version: $CURRENT_VERSION"

# Internal function to increment version
increment_version() {
    local version=$1
    local type=$2
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)
    local patch=$(echo $version | cut -d. -f3)

    case $type in
        major) major=$((major + 1)); minor=0; patch=0 ;;
        minor) minor=$((minor + 1)); patch=0 ;;
        patch) patch=$((patch + 1)) ;;
    esac
    echo "$major.$minor.$patch"
}

NEW_VERSION=$(increment_version $CURRENT_VERSION $BUMP_TYPE)
echo "New version: $NEW_VERSION"

# Update the single canonical source.
sed "s/VERSION = \"$CURRENT_VERSION\"/VERSION = \"$NEW_VERSION\"/" euercli/__init__.py > euercli/__init__.py.tmp && mv euercli/__init__.py.tmp euercli/__init__.py

echo "Successfully bumped canonical version to $NEW_VERSION in euercli/__init__.py"
