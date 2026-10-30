#!/bin/zsh
cd "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6"
a=$(git show 64cfca9:src/deploy_vii/assets/app.css | shasum -a 256 | cut -d' ' -f1)
b=$(git show 3c90773:src/deploy_vii/assets/app.css | shasum -a 256 | cut -d' ' -f1)
c=$(git show 71782af:src/deploy_vii/assets/app.css | shasum -a 256 | cut -d' ' -f1)
echo "64cfca9=$a 3c90773=$b 71782af=$c"
[ "$a" = ea3a8198f9f6f4b4c9a354427460a29cc6b555047a095a916949f8775e75f1ac ] && [ "$b" = 14aa4a822ef30a8827a0152b4b7470883967e558dff409aacea4dcc8c0a5cfd4 ] && [ "$b" = "$c" ]
