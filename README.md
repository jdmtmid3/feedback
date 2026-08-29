# Customer Feedback System

A comprehensive web-based platform for businesses to collect, manage, and analyze customer feedback across multiple store locations.

## 🚀 Features

- **Multi-Store Management**: Track feedback and performance for multiple business locations.
- **Master Questionnaire**: Centralized control over feedback forms with the ability to sync changes to all stores.
- **Live Analytics Dashboard**: Real-time visualization of response volumes, average ratings, and recent activity trends.
- **Dynamic Charting**: interactive bar and line charts for data-driven insights.
- **Automated QA Suite**: Built-in test suite to ensure system stability.
- **Responsive Design**: Modern, orange-themed UI built with Bootstrap 5.

## 🛠️ Tech Stack

- **Backend**: Python / Flask
- **Frontend**: HTML5, CSS3, JavaScript (Chart.js, Sortable.js)
- **Database**: MySQL
- **Environment**: python-dotenv for configuration management

## 📦 Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/YOUR_USERNAME/feedback_system.git
   cd feedback_system
   ```

2. **Set up a virtual environment**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the environment**:
   Create a `.env` file in the root directory with your database credentials:

   ```env
   DB_HOST=localhost
   DB_USER=your_user
   DB_PASSWORD=your_password
   DB_NAME=feedback_system
   DB_PORT=3306
   SECRET_KEY=<generate-a-long-random-secret>
   LICENSING_API_KEY=<generate-a-long-random-shared-key>
   LICENSING_PORTAL_URL=https://feedbacklicensing-production-c938.up.railway.app
   MAIN_APP_URL=http://localhost:8000
   BOOTSTRAP_ADMIN_USERNAME=<only-for-a-new-database>
   BOOTSTRAP_ADMIN_EMAIL=<only-for-a-new-database>
   BOOTSTRAP_ADMIN_PASSWORD=<only-for-a-new-database>
   ```

   For the licensing portal, set these additional variables:

   ```env
   MAIN_APP_URL=http://localhost:8000  # URL of the main feedback system
   LICENSING_API_KEY=<same-shared-key-as-main-app>
   ```

5. **Initialize the database**:
   Ensure your MySQL server is running and the database specified in `.env` exists.

   On Railway, set the exact same non-default `LICENSING_API_KEY` on both the
   main app and licensing portal services. Set `LICENSING_PORTAL_URL` on the
   main app to the public licensing URL, and `MAIN_APP_URL` on the licensing
   portal to the public main-app URL.

6. **Run the application**:
   ```bash
   python3 app.py
   ```

## 🧪 Testing

Run the automated QA test suite:

```bash
source venv/bin/activate && python3 qa_tester.py
```

## 📊 Generating Demo Data

To populate the dashboard with realistic simulation data:

```bash
source venv/bin/activate && python3 generate_realistic_data.py
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
