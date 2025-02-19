# Dùng Python 3.10 làm base image
FROM python:3.10

# Ngăn Python tạo bytecode và đảm bảo log hiển thị liên tục
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt các gói hệ thống cần thiết cho pyodbc và msodbcsql17 trong 1 RUN duy nhất
RUN apt-get update && apt-get install -y \
    curl gnupg2 apt-transport-https unixodbc unixodbc-dev && \
    curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    rm -rf /var/lib/apt/lists/*  # Dọn dẹp cache để giảm dung lượng image

# Copy file requirements trước để tận dụng cache layer của Docker
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && pip install -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . /app/

# Mở cổng 8000 để truy cập
EXPOSE 8000

# Chạy Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]