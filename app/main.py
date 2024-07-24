import gzip
import socket
import sys
import threading

status_codes = {
    200: "OK",
    201: "Created",
    404: "Not Found",
    500: "Internal Server Error"
}


def compress_body(body: bytes, encoding='gzip') -> bytes:
    if encoding == 'gzip':
        return gzip.compress(body)
    else:
        return body


def parse_request(data: str) -> tuple[str, str, dict, str]:
    lines = data.split("\r\n")

    request_line = lines[0].split(" ")
    request_type = request_line[0]
    endpoint = request_line[1]

    headers = {}
    body = lines[-1]

    for line in lines[1:-1]:
        if not line:
            break

        key, value = line.split(": ", 1)
        headers[key] = value

    return request_type, endpoint, headers, body


def generate_response(status_code: int, headers: dict = {}, body: bytes | str = "") -> bytes:
    response = f"HTTP/1.1 {status_code} {status_codes[status_code]}\r\n"

    if status_code == 404 or status_code == 201:
        return f"{response}\r\n".encode()
    elif status_code == 200:
        for key, value in headers.items():
            response += f"{key}: {value}\r\n"

        if body:
            if not isinstance(body, bytes):
                body = body.encode()
            response += f"Content-Length: {len(body)}\r\n"

        return f"{response}\r\n".encode() + body


def request_handler(connection, address, args):
    print(f"Connection from {address}")
    data: str = connection.recv(1024).decode()

    if not data:
        connection.close()

    type, endpoint, headers, body = parse_request(data)

    if endpoint == "/":
        response: bytes = generate_response(
            200, {"Content-Type": "text/plain"}, "Hello, World!")
        connection.sendall(response)

    elif endpoint == "/user-agent":
        user_agent = headers.get("User-Agent", "Unknown")
        response: bytes = generate_response(
            200, {"Content-Type": "text/plain"}, user_agent)
        connection.sendall(response)

    elif endpoint.startswith("/echo/"):
        message = endpoint.split("/echo/")[1]

        response_headers = {
            "Content-Type": "text/plain"
        }

        if headers.get("Accept-Encoding") and "gzip" in headers.get("Accept-Encoding"):
            response_headers["Content-Encoding"] = "gzip"
            message = compress_body(message.encode())

        response = generate_response(
            200, response_headers, message)
        connection.sendall(response)

    elif endpoint.startswith("/files/"):
        try:
            file_path = endpoint.split("/files/")[1]
            directory = args.get("directory", "files")

            if type == "GET":
                with open(f"{directory}/{file_path}", "rb") as file:
                    file_content = file.read()
                    response = generate_response(
                        200, {"Content-Type": "application/octet-stream"}, file_content)
                    connection.sendall(response)

            elif type == "POST":
                with open(f"{directory}/{file_path}", "w") as file:
                    file.write(body)
                    response = generate_response(201)
                    connection.sendall(response)

        except FileNotFoundError:
            response = generate_response(404)
            connection.sendall(response)

    else:
        response = generate_response(404)
        connection.sendall(response)

    connection.close()


def main():
    print("Server is running...")
    port = 4221

    args = {}
    if "--directory" in sys.argv:
        directory_index = sys.argv.index("--directory")
        args["directory"] = sys.argv[directory_index + 1]

    with socket.create_server(("localhost", port), reuse_port=True) as server_socket:
        while True:
            connection, address = server_socket.accept()
            threading.Thread(target=request_handler,
                             args=(connection, address, args)).start()


if __name__ == "__main__":
    main()
