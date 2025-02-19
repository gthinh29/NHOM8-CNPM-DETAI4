# Dùng Python 3.10 làm base image
FROM python:3.10

# Ngăn Python tạo bytecode và đảm bảo log hiển thị liên tục
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Cài đặt các gói hệ thống cần thiết cho pyodbc và msodbcsql17
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    apt-transport-https \
    unixodbc \
    unixodbc-dev

# Thêm kho lưu trữ Microsoft với phương pháp signed-by
RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17


    
# Copy file requirements và cài đặt các package Python
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . /app/


# Chạy Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

