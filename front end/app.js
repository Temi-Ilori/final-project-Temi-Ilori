// app.js - FINAL FRONTEND FOR SPRINT 2
const express = require("express");
const axios = require("axios");
const path = require("path");
const bodyParser = require("body-parser");

const app = express();
console.log("Loaded app.js v3 with /test route");
const PORT = 3000;

// Flask backend base URL
const API_BASE = "http://127.0.0.1:5001";

// View engine & static files
app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));
app.use(express.static(path.join(__dirname, "public")));
app.use(bodyParser.urlencoded({ extended: true }));

// Helper: pull flash-style messages from query string
function getMessages(req) {
  return {
    message: req.query.msg || "",
    error: req.query.err || "",
  };
}

// Simple debug route to confirm frontend is rendering
app.get("/test", (req, res) => {
  res.send("<h1>Frontend is working ✅</h1><p>Go to <a href=\"/recipes\">/recipes</a>.</p>");
});

// Home → send to /recipes
app.get("/", (req, res) => {
  res.redirect("/recipes");
});

/* ==================== RECIPES ==================== */

// GET /recipes – list recipes
app.get("/recipes", async (req, res) => {
  const { message, error } = getMessages(req);
  console.log("GET /recipes – rendering recipes page");

  try {
    const response = await axios.get(`${API_BASE}/recipes`);
    const recipes = response.data || [];
    res.render("recipes", { recipes, message, error });
  } catch (err) {
    console.error("Error fetching recipes:", err.message);
    res.render("recipes", {
      recipes: [],
      message,
      error: "Failed to load recipes from backend.",
    });
  }
});

// POST /recipes – create recipe
app.post("/recipes", async (req, res) => {
  const { name, instructions } = req.body;

  if (!name || !instructions) {
    return res.redirect(
      "/recipes?err=" +
        encodeURIComponent("Name and instructions are required.")
    );
  }

  try {
    await axios.post(`${API_BASE}/recipes`, { name, instructions });
    res.redirect("/recipes?msg=" + encodeURIComponent("Recipe created."));
  } catch (err) {
    console.error("Error creating recipe:", err.message);
    res.redirect(
      "/recipes?err=" + encodeURIComponent("Failed to create recipe.")
    );
  }
});

// POST /recipes/:id/update – update recipe
app.post("/recipes/:id/update", async (req, res) => {
  const { id } = req.params;
  const { name, instructions } = req.body;

  try {
    await axios.put(`${API_BASE}/recipes/${id}`, { name, instructions });
    res.redirect("/recipes?msg=" + encodeURIComponent("Recipe updated."));
  } catch (err) {
    console.error("Error updating recipe:", err.message);
    res.redirect(
      "/recipes?err=" + encodeURIComponent("Failed to update recipe.")
    );
  }
});

// POST /recipes/:id/delete – delete recipe
app.post("/recipes/:id/delete", async (req, res) => {
  const { id } = req.params;

  try {
    await axios.delete(`${API_BASE}/recipes/${id}`);
    res.redirect("/recipes?msg=" + encodeURIComponent("Recipe deleted."));
  } catch (err) {
    console.error("Error deleting recipe:", err.message);
    res.redirect(
      "/recipes?err=" + encodeURIComponent("Failed to delete recipe.")
    );
  }
});

// POST /recipes/:id/cook – call /cook on backend
app.post("/recipes/:id/cook", async (req, res) => {
  const { id } = req.params;

  try {
    const response = await axios.post(`${API_BASE}/cook`, {
      recipeid: parseInt(id, 10),
    });
    const data = response.data || {};
    const msg =
      data.message || (data.can_cook ? "Cooked successfully." : "Cannot cook.");
    res.redirect("/recipes?msg=" + encodeURIComponent(msg));
  } catch (err) {
    console.error("Error cooking recipe:", err.message);
    res.redirect(
      "/recipes?err=" + encodeURIComponent("Failed to cook this recipe.")
    );
  }
});

/* ==================== INGREDIENTS ==================== */

// GET /ingredients – list ingredients
app.get("/ingredients", async (req, res) => {
  const { message, error } = getMessages(req);
  console.log("GET /ingredients – rendering ingredients page");

  try {
    const response = await axios.get(`${API_BASE}/ingredients`);
    const ingredients = response.data || [];
    res.render("ingredients", { ingredients, message, error });
  } catch (err) {
    console.error("Error fetching ingredients:", err.message);
    res.render("ingredients", {
      ingredients: [],
      message,
      error: "Failed to load ingredients from backend.",
    });
  }
});

// POST /ingredients – create ingredient
app.post("/ingredients", async (req, res) => {
  const { ingredientname, totalamount } = req.body;

  if (!ingredientname || !totalamount) {
    return res.redirect(
      "/ingredients?err=" +
        encodeURIComponent("Ingredient name and amount are required.")
    );
  }

  try {
    await axios.post(`${API_BASE}/ingredients`, {
      ingredientname,
      totalamount: parseInt(totalamount, 10),
    });
    res.redirect(
      "/ingredients?msg=" + encodeURIComponent("Ingredient created.")
    );
  } catch (err) {
    console.error("Error creating ingredient:", err.message);
    res.redirect(
      "/ingredients?err=" + encodeURIComponent("Failed to create ingredient.")
    );
  }
});

// POST /ingredients/:id/update – update ingredient
app.post("/ingredients/:id/update", async (req, res) => {
  const { id } = req.params;
  const { ingredientname, totalamount } = req.body;

  try {
    await axios.put(`${API_BASE}/ingredients/${id}`, {
      ingredientname,
      totalamount: parseInt(totalamount, 10),
    });
    res.redirect(
      "/ingredients?msg=" + encodeURIComponent("Ingredient updated.")
    );
  } catch (err) {
    console.error("Error updating ingredient:", err.message);
    res.redirect(
      "/ingredients?err=" + encodeURIComponent("Failed to update ingredient.")
    );
  }
});

// POST /ingredients/:id/delete – delete ingredient
app.post("/ingredients/:id/delete", async (req, res) => {
  const { id } = req.params;

  try {
    await axios.delete(`${API_BASE}/ingredients/${id}`);
    res.redirect(
      "/ingredients?msg=" + encodeURIComponent("Ingredient deleted.")
    );
  } catch (err) {
    console.error("Error deleting ingredient:", err.message);
    const msg =
      "Failed to delete ingredient. It might be used in a recipe (foreign key).";
    res.redirect("/ingredients?err=" + encodeURIComponent(msg));
  }
});

/* ==================== RECIPE + INGREDIENTS ==================== */

// GET /recipeingredients – show recipe + ingredients page
app.get("/recipeingredients", async (req, res) => {
  const { message, error } = getMessages(req);
  const selectedRecipeId = req.query.recipeid || "";
  console.log("GET /recipeingredients – selectedRecipeId =", selectedRecipeId);

  try {
    const [recipesResp, ingResp] = await Promise.all([
      axios.get(`${API_BASE}/recipes`),
      axios.get(`${API_BASE}/ingredients`),
    ]);

    const recipes = recipesResp.data || [];
    const ingredients = ingResp.data || [];

    let recipeIngredients = [];
    if (selectedRecipeId) {
      const riResp = await axios.get(
        `${API_BASE}/recipeingredients?recipeid=${selectedRecipeId}`
      );
      recipeIngredients = riResp.data || [];
    }

    res.render("recipeingredients", {
      recipes,
      ingredients,
      selectedRecipeId,
      recipeIngredients,
      message,
      error,
    });
  } catch (err) {
    console.error("Error loading recipeingredients page:", err.message);
    res.render("recipeingredients", {
      recipes: [],
      ingredients: [],
      selectedRecipeId,
      recipeIngredients: [],
      message,
      error: "Failed to load data from backend.",
    });
  }
});

// POST /recipeingredients – add ingredient to recipe
app.post("/recipeingredients", async (req, res) => {
  const { recipeid, ingredientid, amount } = req.body;

  if (!recipeid || !ingredientid || !amount) {
    return res.redirect(
      "/recipeingredients?recipeid=" +
        encodeURIComponent(recipeid || "") +
        "&err=" +
        encodeURIComponent("Recipe, ingredient, and amount are required.")
    );
  }

  try {
    await axios.post(`${API_BASE}/recipeingredients`, {
      recipeid: parseInt(recipeid, 10),
      ingredientid: parseInt(ingredientid, 10),
      amount: parseInt(amount, 10),
    });

    res.redirect(
      "/recipeingredients?recipeid=" +
        encodeURIComponent(recipeid) +
        "&msg=" +
        encodeURIComponent("Ingredient added to recipe.")
    );
  } catch (err) {
    console.error("Error creating recipeingredient:", err.message);
    res.redirect(
      "/recipeingredients?recipeid=" +
        encodeURIComponent(recipeid) +
        "&err=" +
        encodeURIComponent("Failed to add ingredient to recipe.")
    );
  }
});

app.listen(PORT, () => {
  console.log(`Frontend running at http://127.0.0.1:${PORT}`);
});
