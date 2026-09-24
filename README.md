# MEV

İnternetsiz çalışan küçük bir karar motoru ve dosya bulucu. Metin üretmez,
tahmin yürütmez; hazır seçeneklerden birini ve ne kadar emin olduğunu söyler.

![MEV demosu](assets/demo.svg)

## Ne işe yarar

1. **Karar verir.** Gelen yazıyı okuyup hangi birime/etikete ait olduğunu söyler.
   Örnek: "faturamda çift çekim var" → billing, güven 0.93.
2. **Dosya bulur.** Büyük repoda niyet cümlesiyle arama yapar.
   Örnek: "ödeme iade akışı nerede?" → ilgili dosyalar, olasılık sırasıyla.
3. **Dili tespit eder.** Metnin dilini milisaniyenin altında bulur.

Hepsi bu bilgisayarda çalışır. Dışarıya veri gitmez, API ücreti yok.

## Kurulum

Tek komut. Windows:

```powershell
powershell -ExecutionPolicy Bypass -File kur.ps1
```

macOS / Linux:

```bash
bash install.sh
```

Bu komut testleri çalıştırır, skill'i ajanların göreceği yerlere kopyalar
(opencode, claude, agents) ve MCP kaydını ekrana yazar.

**Son adım, şart:** IDE'yi kapatıp yeniden açın (Cursor, Antigravity, terminal
fark etmez). MCP sunucuları ve skill'ler açılışta yüklenir; yeniden
başlatmadan görünmez.

Ajanınıza tek cümle söylemeniz yeter: **"mev kur"** veya **"mev skill'ini kur"**.
Gerisini skill dosyasındaki talimat halleder.

## Kullanım

Kokpit (tarayıcı paneli, 4 bölme: karar, dosya bul, dil, agent):

```powershell
python dashboard.py
# http://127.0.0.1:47921 — port özellikle seçildi, yaygın portlarla çakışmaz
```

MCP olarak — hangisini kullanıyorsanız onu ekleyin, hepsi aynı kapı:

opencode.json:
```json
{"mcp": {"mev": {"type": "local",
  "command": ["python", "C:/yol/Mev/mcp_server.py"], "enabled": true}}}
```

Claude Code (`.mcp.json`, proje köküne):
```json
{"mcpServers": {"mev": {"command": "python",
  "args": ["C:/yol/Mev/mcp_server.py"]}}}
```

Cursor (`.cursor/mcp.json`) ve Antigravity (MCP ayarlarına JSON olarak):
```json
{"mcpServers": {"mev": {"command": "python",
  "args": ["C:/yol/Mev/mcp_server.py"]}}}
```

Skill her ajanda aynı çalışır: `.opencode/skills/mev/`, `.claude/skills/mev/`
veya `.agents/skills/mev/` altına `SKILL.md` koyun (`kur.ps1` bunu otomatik yapar).
Ajanınıza tek cümle söylemeniz yeter: **"mev kur"**.

## Araçlar

| Araç | Girdi | Çıktı |
|---|---|---|
| `decide` | durum + sorular (`choice`/`noul`/`score`) | seçenek + olasılık + güven |
| `sfind` | sorgu + repo kökü (`semantic`/`exact`) | sıralı dosya + snippet + güven |
| `route` | metin | dil/model + gerekçe |

Kural: güven 0.85 ve üstü otomatik devam, 0.50 altı insana sorulur.

## Rakiplerden farkı

Aynı işi yapanlara karşı dürüst tablo. Sayılar kendi ölçümlerimiz ve
yayınlanan belgeler; ilk sütun MEV'in iddiası değil, ölçümüdür.

| Boyut | MEV | Jev (TypeSafe, hosted API) | Laya (açık kaynak) | Graft | ripgrep |
|---|---|---|---|---|---|
| Ne yapar | tip'li karar + niyetle dosya bulma | tip'li karar API'si | tip'li karar modeli | repo anlam haritası | birebir string arama |
| Kurulum | yok (stdlib) | API anahtarı | ~650MB ağırlık + torch | CLI + (derin modda) LLM anahtarı | tek binary |
| Karar süresi | ~0.14ms, CPU | ağ gecikmesi (100ms+) | ~33ms GPU / ~300ms CPU | graf okuma, ms mertebesi | — |
| Niyetle arama (490 dosya) | 30-130ms sıcak | — (karar modeli, arama yapmaz) | — (karar modeli) | node üzerinden hızlı | ~131ms ama niyeti anlamaz |
| Türkçe niyet → İngilizce kod | bulur | — | 100+ dilde anlar (bizden iyi) | semantik düğümlerle bulur | 0 sonuç |
| Maliyet | $0, offline | token başına ücret | $0 (kendi GPU'n) | derin modda token ücreti | $0 |
| Doğruluk (dar görev) | ~%87 | yüksek (kapalı kutu) | %45-77 (göreve göre, yayınlanan) | +12 puan (SWE-bench, kendi ölçümleri) | %100 (bulursa) |
| Zayıf yanı | genel sorularda %60-75 | kapalı, dışa bağımlı | kurulum ağır, sıfır-atışta dalgalı | kurulum + bakım ister | anlamaz, sadece eşleşir |

Özet: birebir aramada ripgrep'i geçemeyiz, geçmeye de çalışmıyoruz. MEV,
grep'in **bulamadığını** bulan ve Jev/Laya'nın **karar katmanını** internetsiz,
kurulumsuz veren küçük parçadır. Graft ile rakip değil tamamlayıcıdır:
harita ondan, hızlı karar bizden.

## Ölçümler

Kendi makinemizde ölçtük, tekrarlanabilir (`test_all.py`, `bench_repo.py`):

| Deney | Sonuç |
|---|---|
| Otomatik test | 23/23 geçti |
| 308 dosyalık repo, 5 soru | 5'te 5 ilk-sıra isabet |
| Tek karar süresi | ~0.14ms |
| 490 dosyalık gerçek proje, sıcak arama | 30-130ms |
| Türkçe niyet → İngilizce kod | grep 0 sonuç, MEV ilgili dosyayı buluyor |

## Sınırlar

- %100 doğruluk yok. Dar görevlerde ~%87, genel sorularda %60-75 bekleyin.
- Sohbet etmez, kod üretmez.
- Sözlük ve ağırlıklar sınırlı; bilmediği alanda güveni düşürür, ki doğrusu budur.
- 2000+ dosyada ilk tarama yavaşlayabilir; `index:true` açın (`.mevidx` yazar).

## Dosyalar

`mev.py` (motor), `mcp_server.py` (MCP sunucusu), `dashboard.py` (panel),
`index_cache.py`, `distilled_tasks.json` (damıtılmış ağırlıklar, 79KB),
`test_all.py`, `bench_repo.py`, `.opencode/skills/mev/SKILL.md`.
Bağımlılık yok, tamamı standart kütüphane.

## Lisans

MIT. Ayrıntı için `LICENSE` dosyasına bakın.

---

*"Hayatta en hakiki mürşit ilimdir, fendir." — Mustafa Kemal Atatürk*
