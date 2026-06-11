# Django Blog & Translator

A feature-rich Django-based blogging platform that combines content publishing, user interaction, profile management, messaging, and translation capabilities into a modern web application.

## Features

### Authentication & User Management

* User Registration and Login
* Email Verification & Account Activation
* Password Change Functionality
* Custom User Model
* User Profiles with Avatars
* Follow / Unfollow Users

### Blog Management

* Create, Edit, and Delete Blog Posts
* Draft / Pending / Published Workflow
* Category-Based Organization
* Rich Text Editing with TinyMCE
* Content Sanitization and Security Controls

### Social Features

* Likes and Dislikes
* Nested Comment System
* Post Sharing
* User Activity Tracking
* Follow System

### Messaging

* User-to-User Conversations
* Inbox Management
* Real-Time Messaging Support

### Dashboard

* Author Dashboard
* Post Management
* Profile Statistics
* Activity Monitoring

## Technology Stack

### Backend

* Python
* Django
* Django Channels

### Frontend

* HTML5
* CSS3
* Bootstrap 5
* JavaScript
* AJAX

### Database

* SQLite (Development)

### Additional Libraries

* TinyMCE
* Bleach
* BeautifulSoup4
* Django Ratelimit
* Python Decouple

## Installation

### Clone the Repository

```bash
git clone https://github.com/yourusername/django-blog-translator.git
cd django-blog-translator
```

### Create a Virtual Environment

```bash
python -m venv venv
```

### Activate the Virtual Environment

Windows:

```bash
venv\Scripts\activate
```

Linux / macOS:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file:

```env
SECRET_KEY=your-secret-key
DEBUG=True
```

### Apply Migrations

```bash
python manage.py migrate
```

### Create a Superuser

```bash
python manage.py createsuperuser
```

### Run the Development Server

```bash
python manage.py runserver
```

## Security Notes

* Do not commit `.env` files.
* Do not commit production database files.
* Rotate any exposed credentials before deployment.
* Keep `SECRET_KEY` private.

## License

This project is proprietary software.

The source code is provided for educational, evaluation, portfolio-review, and learning purposes only.

Commercial use, redistribution, deployment, resale, sublicensing, or creation of competing products based on this codebase are prohibited without explicit written permission from the author.

See the `LICENSE` file for full terms and conditions.

## Author

**Sagar Samadder**

Computer Engineering Student
Full-Stack Developer

Technologies: Python, Django, JavaScript, Bootstrap, SQL
