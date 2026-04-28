# tasklin-project
# 🚀 Tasklin – Smart Hackathon Finder

Tasklin is a web application that helps students discover hackathons and find teammates efficiently using smart search and matching.

---

## 🌟 Features

### 🔍 Hackathon Finder
- Search hackathons using keywords
- Smart filtering across title, location, and date
- Clean and interactive UI
- Direct links to hackathon pages

### 🤝 Teammate Finder
- Add your profile (skills, interests, contact)
- Find teammates based on skill matching
- Highlighted “Good Match” suggestions

---

## 🧠 How It Works

- Backend (Flask) serves hackathon and user data via APIs
- Frontend (Streamlit) fetches and displays data dynamically
- Smart keyword matching improves search experience
- Skill matching helps users connect with relevant teammates

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **Backend:** Flask
- **API Communication:** Requests
- **Data Storage:** JSON

---

## 📂 Project Structure
tasklin-project/
│
├── backend/
│ └── app.py
│
├── frontend/
│ └── ui.py
│
├── data/
│ ├── hackathons.json
│ └── users.json
│
├── requirements.txt
└── README.md

---

## ▶️ How to Run

### 1️⃣ Start Backend

```bash
cd backend
python app.py