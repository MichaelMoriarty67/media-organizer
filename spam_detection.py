from flask import Flask, jsonify, request, send_file, render_template_string
import threading
import webbrowser


def is_screenshot(file_name: str) -> bool:
    """Basic heuristic to determine if a file is a screenshot based on its name."""
    name = file_name.lower()
    return (
        "screenshot" in name
        or "screen shot" in name
        or "スクリーンショット" in name
        or name.startswith("screenshot_")
        or name.startswith("screen_capture")
    )


def create_app(spam_paths):
    app = Flask(__name__)
    # Convert spam_paths (List[Path]) to a list of absolute paths as strings
    spam_paths = [p.resolve() for p in spam_paths]

    # Map filenames to full paths for lookup
    filename_to_path = {p.name: p for p in spam_paths}

    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Image Review</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        text-align: center;
        margin: 20px;
        background: #f0f0f0;
      }
      #image-container {
        margin-bottom: 10px;
      }
      #image-container img {
        max-width: 80vw;
        max-height: 80vh;
        border: 3px solid #333;
        background: white;
      }
      #info {
        margin-bottom: 15px;
        font-weight: bold;
      }
      button {
        font-size: 1.2em;
        padding: 10px 20px;
        margin: 0 15px;
        cursor: pointer;
      }
      button:focus {
        outline: 2px solid blue;
      }
    </style>
    </head>
    <body>

    <div id="info">Loading images...</div>
    <div id="image-container">
      <img id="main-image" src="" alt="Image to review" />
    </div>

    <button id="keep-btn">Keep [K]</button>
    <button id="delete-btn">Delete [D]</button>

    <script>
      let imageList = [];
      let currentIndex = 0;

      const info = document.getElementById("info");
      const mainImage = document.getElementById("main-image");
      const keepBtn = document.getElementById("keep-btn");
      const deleteBtn = document.getElementById("delete-btn");

      async function fetchImages() {
        const res = await fetch("/api/images");
        imageList = await res.json();
        currentIndex = 0;
        updateView();
      }

      function updateView() {
        if (imageList.length === 0) {
          info.textContent = "No images left to review.";
          mainImage.src = "";
          keepBtn.disabled = true;
          deleteBtn.disabled = true;
          return;
        }
        const currentImage = imageList[currentIndex];
        mainImage.src = "/image/" + encodeURIComponent(currentImage);
        info.textContent = `Reviewing: ${currentImage} (${currentIndex + 1} / ${imageList.length})`;
        keepBtn.disabled = false;
        deleteBtn.disabled = false;
      }

      async function keepImage() {
        advance();
      }

      async function deleteImage() {
        const filename = imageList[currentIndex];
        const res = await fetch("/api/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filename }),
        });
        if (res.ok) {
          imageList.splice(currentIndex, 1);
          if (currentIndex >= imageList.length) {
            currentIndex = imageList.length - 1;
          }
          updateView();
        } else {
          alert("Failed to delete image.");
        }
      }

      function advance() {
        currentIndex++;
        if (currentIndex >= imageList.length) {
          currentIndex = imageList.length - 1;
        }
        updateView();
      }

      keepBtn.addEventListener("click", keepImage);
      deleteBtn.addEventListener("click", deleteImage);

      window.addEventListener("keydown", (e) => {
        if (e.key === "k" || e.key === "K") {
          e.preventDefault();
          keepImage();
        } else if (e.key === "d" || e.key === "D") {
          e.preventDefault();
          deleteImage();
        }
      });

      fetchImages();
    </script>

    </body>
    </html>
    """

    @app.route("/")
    def index():
        return render_template_string(HTML_TEMPLATE)

    @app.route("/api/images")
    def api_images():
        # Return list of filenames currently known
        return jsonify(list(filename_to_path.keys()))

    @app.route("/image/<filename>")
    def serve_image(filename):
        path = filename_to_path.get(filename)
        if not path or not path.exists():
            return "Image not found", 404
        return send_file(path)

    @app.route("/api/delete", methods=["POST"])
    def api_delete():
        data = request.get_json()
        filename = data.get("filename")
        if not filename or filename not in filename_to_path:
            return jsonify({"error": "Invalid filename"}), 400
        path = filename_to_path.pop(filename)
        try:
            path.unlink()
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


def run_review_spam_images_app(
    spam_paths, host="127.0.0.1", port=5000, open_browser=True
):
    app = create_app(spam_paths)

    def open_browser_func():
        import time

        time.sleep(1)
        webbrowser.open(f"http://{host}:{port}")

    if open_browser:
        threading.Thread(target=open_browser_func).start()

    app.run(host=host, port=port, debug=True)
