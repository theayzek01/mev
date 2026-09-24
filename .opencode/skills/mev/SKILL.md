---
name: mev
description: MEV karar motoru ve semantik dosya bulucu. grep yerine sfind kullan, metin uretmeden choice-noul-score karari ver, dili tespit et. Ryuko-AI dahil her repo kokunde calisir.
---

# MEV — sen şusun

Sen bu projede **MEV**'i kullanan kodlama ajanısın. MEV, bu makinede internetsiz
çalışan küçük bir karar motoru + dosya bulucudur. Metin üretmez, uydurmaz;
hazır seçeneklerden birini ve eminlik oranını (confidence) söyler.

## Çalıştırma

**1. MCP kaydı (opencode.json, stdio — port gerekmez):**
```json
{"mcp": {"mev": {"type": "local",
  "command": ["python", "C:/Users/theay/OneDrive/Desktop/Mev/mcp_server.py"],
  "enabled": true}}}
```

**2. İnsan kokpiti (HTTP, port: 47921 — başka hiçbir şeyle çakışmaz):**
```powershell
python C:/Users/theay/OneDrive/Desktop/Mev/dashboard.py
# tarayıcı otomatik açılır: http://127.0.0.1:47921
# Kapatmak için terminalde Ctrl+C. Port özellikle 47921 seçildi;
# 8080/3000/5000/8000'deki servislere bulaşmaz.
```

## Kurulumdan sonra (önemli)

Skill/MCP eklendikten sonra IDE'yi kapatıp yeniden aç
(Cursor / Antigravity / terminal fark etmez). MCP sunucuları ve skill'ler
açılışta yüklenir; yeniden başlatmadan görünmez. Kullanıcıya "mev kur" dediğinde
önce kurulumu yap, sonra bu yeniden başlatma notunu mutlaka söyle.

## Araçlar

| Araç | Ne yapar | Kritik parametreler |
|---|---|---|
| `decide` | `state` + `questions` alır, `choice`/`noul`/`score` + olasılık döner | `state`, `questions:{id:{type,instructions,criteria}}`, `model?` |
| `sfind` | **grep yerine.** Niyetle (`semantic`) veya birebir (`exact`) dosya bulur | `query`, `root`, `top_k`, `mode`, `use_regex`, `case_sensitive`, `context`, `include`, `index` |
| `route` | Dil/script tespiti, <0.5ms | `text` |

## Demir kurallar (grep'in yerini alma protokolü)

1. **Dosya ararken ÖNCE `sfind mode=semantic` kullan.** `grep`/`Select-String`'e ancak
   `exact` bir string (hata kodu, fonksiyon adı) arıyorsan in.
2. Doğal dil niyet ("ödeme iade akışı nerede?") → `semantic`. Sonuçlar
   `probability` + `confidence` + `snippet` ile gelir; ilk sırayı körü körüne alma.
3. `confidence >= 0.85` → otomatik devam et, onay bekleme.
4. `0.50–0.84` → top-3 sonucu gösterip devam et.
5. `confidence < 0.50` → DUR, tahminle işlem yapma, insana sor.
6. `semantic` boş dönerse (`best_effort` hariç) `exact`'e düş, tersini yapma.
7. `root` parametresini her zaman repo köküne ver (örn. Ryuko-AI yolu). cwd'ye güvenme.
8. `top_k` monorepoda 8-12; 25'i geçme. Bütçe 1500ms — `timed_out:true` gelirse
   `include` ile daralt (örn. `".dart"`).
9. Sınıflandırma/yönlendirme kararı için `decide` kullan; cevabı asla serbest
   metin LLM'e tamamlama — `choice` dışına çıkılmaz.
10. Türkçe sorgu İngilizce içeriği bulur (180 girdilik sözlük + damıtılmış ağırlıklar),
    ama genel çeviri bekleme; bulamazsa düşük güven döner — bu doğru davranıştır.

## Örnek akışlar

**A. "Checkout ekranı nerede?" (Flutter repo):**
```
sfind(query="checkout bottom sheet", root="C:/Users/theay/OneDrive/Desktop/Ryuko-AI", top_k=8, mode="semantic")
→ *_bottom_sheet.dart dosyaları olasılık sırasıyla gelir
```

**B. Hata kodu avı:**
```
sfind(query="permission-denied", root="<repo>", mode="exact", context=2)
→ satır numaralı, ±2 bağlam satırlı sonuçlar
```

**C. Bilet triage:**
```
decide(state="Faturamda çift çekim var", questions={"ekip":
  {"type":"choice","instructions":"Hangi ekip?",
   "criteria":{"billing":"fatura iade ücret","technical":"hata çökme"}}})
→ {"choice":"billing","confidence":0.93} → otomatik yönlendir
```

## Sınırlar (dürüst ol)

- %100 doğruluk yok; dar görevlerde ~%87, genel sorularda %60-75 bekle.
- `decide` sohbet etmez, kod üretmez.
- 2000+ dosyada soğuk tarama bütçeyi zorlayabilir → `index:true` (`.mevidx` yazar) aç.
- Sonuçta olmayan dosya adı önerirsen bu HALÜSİNASYONDUR — path'leri aynen aktar.
