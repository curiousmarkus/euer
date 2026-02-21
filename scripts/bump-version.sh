#!/bin/bash
# script to bump version in pyproject.toml and euercli/__init__.py
set -e

BUMP_TYPE=$1
if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo "Usage: $0 {major|minor|patch}"
    exit 1
fi

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep -m 1 "version =" pyproject.toml | sed -E 's/version = "(.*)"/\1/')
if [ -z "$CURRENT_VERSION" ]; then
    echo "Error: Could not find current version in pyproject.toml"
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

# Update pyproject.toml
sed "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml > pyproject.toml.tmp && mv pyproject.toml.tmp pyproject.toml

# Update euercli/__init__.py
sed "s/VERSION = \"$CURRENT_VERSION\"/VERSION = \"$NEW_VERSION\"/" euercli/__init__.py > euercli/__init__.py.tmp && mv euercli/__init__.py.tmp euercli/__init__.py

echo "Successfully bumped version to $NEW_VERSION in pyproject.toml and euercli/__init__.py"
