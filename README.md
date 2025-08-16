# 🛠️ Dataset Tools – AI Dataset Generator Repository

Ushbu repository turli **AI dataset generator** vositalarining to‘plamidir.  
Har bir generator (tool) **alohida branch** sifatida saqlanadi.  
👉 Shuning uchun **o‘ziga kerak bo‘lgan tool’ni tanlab, o‘sha branchni yuklab olish** tavsiya etiladi.

---

## 🔹 Main branch nimani o‘z ichiga oladi?

`main` branch – **faqat umumiy konfiguratsiyalar va qo‘llanma** uchun ishlatiladi:

| Narsa                | Tavsifi                                                                   |
|----------------------|---------------------------------------------------------------------------|
| `README.md`          | Ushbu qo‘llanma (umumiy)                                                  |
| `.gitignore`         | Barcha branchlar uchun umumiy ignore qoidalari                           |
| `utils/`             | Barcha toolslar foydalanishi mumkin bo‘lgan umumiy helper funksiyalar     |
| `tools/`             | **Faqat** har bir tool uchun `README_tool.md` fayl(lar)i (*kod yo‘q*)     |

> ✅ Main branchda **hech qanday ishlaydigan tool kodi yo‘q**  
> ❌ Barcha tool kodlari tegishli **branchlarda** saqlanadi

---

## 🔹 Branchlar va tool’lar

| Tool nomi                | Branch nomi             |
|--------------------------|--------------------------|
| Text-to-JSON Generator   | `tool-text-json`          |
| Q&A Dataset Builder      | `tool-qa-builder`         |
| Multi-topic Generator    | `tool-multi-generator`    |

---

## 🔽 Tool’ni yuklab olish usullari

### 🔧 1. Faqat bitta toolni yuklab olish (to‘g‘ridan-to‘g‘ri branch bilan)

```bash
git clone --branch tool-text-json git@github.com:SaidAbbos96/dataset-tools.git

### 🔧 2. Umumiy repo + keyin branchga o‘tish

```bash
git clone git@github.com:SaidAbbos96/dataset-tools.git
cd dataset-tools

# mavjud branchlar ro'yxati
git branch -a

# kerakli toolga o‘tish
git checkout tool-text-json

# klonlash (umumiy yoki ma'lum branch bilan)
git clone <repo>

# yangi branch yaratish (agar yangi tool qo‘shayotgan bo‘lsangiz)
git checkout -b <tool-branch-name>

# yoki mavjud tool branchiga o‘tish
git checkout <tool-branch-name>

# o‘zgartirishlar
git add .
git commit -m "..."
git push -u origin <tool-branch-name>

🔔 Eslatma

#Har bir tool branch ichida alohida:

.gitignore

README_tool.md

requirements.txt

src/, config/, venv/ va boshqa papkalar

bo‘lishi mumkin (mustaqil loyiha sifatida qaraladi).

