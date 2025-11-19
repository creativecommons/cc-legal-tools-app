const express = require("express");
const prettier = require("prettier");

const app = express();

// https://expressjs.com/en/5x/api.html#express.text
//
// As of 2025-11-19, the largest file in cc-legal-tools-data/docs is 7.5K
app.use(express.text({ limit: "2mb", type: "*/*" }));

app.post("/", async (req, res) => {
  try {
    const formatted = await prettier.format(req.body, { parser: "html" });
    res.type("text/html").send(formatted);
  } catch (error) {
    res
      .status(500)
      .type("text/plain")
      .send(`Prettier error:\n${error.message}`);
  }
});

const server = app.listen(3000);

process.on("SIGINT", () => {
  server.close(() => process.exit(0));
});
