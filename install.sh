#!/usr/bin/env bash
# MEV kurulum — tek komut:
#   bash install.sh
set -euo pipefail
MEV_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$MEV_DIR/.opencode/skills/mev/SKILL.md" ] || { echo "SKILL.md bulunamadi: $MEV_DIR"; exit 1; }
echo "Klasor: $MEV_DIR"
command -v python3 >/dev/null || { echo "Python3 bulunamadi."; exit 1; }
python3 --version

echo "[1/3] Dogrulama calistiriliyor..."
python3 "$MEV_DIR/test_all.py" 2>&1 | tail -1
test "${PIPESTATUS[0]}" -eq 0 || { echo "Testler basarisiz. Durduruldu."; exit 1; }

echo "[2/3] Skill kopyalaniyor..."
for t in "$HOME/.config/opencode/skills/mev" "$HOME/.claude/skills/mev" "$HOME/.agents/skills/mev"; do
  mkdir -p "$t"
  cp "$MEV_DIR/.opencode/skills/mev/SKILL.md" "$t/SKILL.md"
  echo "  + $t"
done

echo "[3/3] MCP kaydi (opencode.json'a ekle):"
echo "  {\"mcp\":{\"mev\":{\"type\":\"local\",\"command\":[\"python3\",\"$MEV_DIR/mcp_server.py\"],\"enabled\":true}}}"

echo ""
echo "Bitti. SON ADIM (sart): IDE'yi kapatip yeniden ac."
echo "MCP ve skill'ler acilista yuklenir, yeniden baslatmadan gorunmez."
echo "Kokpit: python3 \"$MEV_DIR/dashboard.py\"  ->  http://127.0.0.1:47921"
