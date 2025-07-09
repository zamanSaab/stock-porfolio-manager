# Stock Portfolio Project

This is a Django project named **stock_portfolio** designed to manage stock portfolios. It includes an app called **stocks** which allows users to manage brokers and their associated financial data.

## Project Structure

The project consists of the following files and directories:

- **manage.py**: Command-line utility for interacting with the Django project.
- **stock_portfolio/**: Main project directory containing configuration files.
  - **__init__.py**: Indicates that this directory should be treated as a Python package.
  - **settings.py**: Configuration settings for the Django project.
  - **urls.py**: URL patterns for the project.
  - **asgi.py**: ASGI support for handling asynchronous requests.
  - **wsgi.py**: WSGI support for serving HTTP requests.
- **stocks/**: Django app for managing stock brokers.
  - **__init__.py**: Indicates that this directory should be treated as a Python package.
  - **admin.py**: Registers the Broker model with the Django admin site.
  - **apps.py**: Configuration for the stocks app.
  - **migrations/**: Directory for database migrations.
    - **__init__.py**: Indicates that this directory should be treated as a Python package.
  - **models.py**: Defines the Broker model with fields for name, code, total amount, and free amount.
  - **tests.py**: Contains tests for the stocks app.
  - **views.py**: Contains views for the stocks app.

## Setup Instructions

1. **Install Django**: Make sure you have Django installed in your environment. You can install it using pip:
   ```
   pip install django
   ```

2. **Create the Project**: Navigate to your desired directory and create the project:
   ```
   django-admin startproject stock_portfolio
   ```

3. **Create the App**: Change into the project directory and create the stocks app:
   ```
   cd stock_portfolio
   python manage.py startapp stocks
   ```

4. **Configure the App**: Add 'stocks' to the `INSTALLED_APPS` list in `settings.py`.

5. **Run Migrations**: Apply the initial migrations:
   ```
   python manage.py migrate
   ```

6. **Run the Development Server**: Start the development server to see your project in action:
   ```
   python manage.py runserver
   ```

## Usage

You can access the Django admin interface to manage brokers by navigating to `http://127.0.0.1:8000/admin/` after starting the server. Make sure to create a superuser to log in to the admin site.

## License

This project is licensed under the MIT License.