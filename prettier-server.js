const express = require("express");
const prettier = require("prettier");

const app = express();

app.use(express.text({ limit: "10mb", type: "*/*" }));

app.post("/", async (req, res) => {
  try {
    const formatted = await prettier.format(req.body, { parser: "html" });
    res.type("text/html").send(formatted);
  } catch (error) {
    res.status(500).type("text/plain").send(`Prettier error: ${error.message}`);
  }
});

const server = app.listen(3000);

process.on("SIGINT", () => {
  server.close(() => process.exit(0));
});
