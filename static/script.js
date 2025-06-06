async function searchFood() {
  const query = document.getElementById('searchInput').value;
  const response = await fetch('https://fatsecret.onrender.com/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });

  const data = await response.json();
  const foods = data.foods?.food || [];
  const resultsDiv = document.getElementById('results');
  resultsDiv.innerHTML = '';

  if (foods.length === 0) {
    resultsDiv.textContent = 'No results found.';
    return;
  }

  foods.forEach(food => {
    const foodContainer = document.createElement('div');
    foodContainer.style.marginBottom = '15px';

    const p = document.createElement('p');
    p.textContent = `${food.food_name} (${food.brand_name || 'Generic'})`;
    p.style.cursor = 'pointer';
    p.style.fontWeight = 'bold';

    const nutritionDiv = document.createElement('div');
    nutritionDiv.style.marginLeft = '10px';
    nutritionDiv.style.display = 'none';

    p.onclick = async () => {
      const nutrition = await getNutrition(food.food_id);
      if (!nutrition) {
        nutritionDiv.innerHTML = '<i>Nutrition data not available.</i>';
      } else {
        nutritionDiv.innerHTML = `
          <ul>
            <li>Calories: ${nutrition.calories}</li>
            <li>Protein: ${nutrition.protein}g</li>
            <li>Fat: ${nutrition.fat}g</li>
            <li>Carbs: ${nutrition.carbohydrate}g</li>
          </ul>
        `;
      }
      nutritionDiv.style.display = 'block';
    };

    foodContainer.appendChild(p);
    foodContainer.appendChild(nutritionDiv);
    resultsDiv.appendChild(foodContainer);
  });
}

async function getNutrition(food_id) {
  const response = await fetch('https://fatsecret.onrender.com/food_details', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ food_id })
  });

  const data = await response.json();

  const servingData = data.food?.servings?.serving;

  if (!servingData) return null;

  // ✅ Handle both object and array response
  const serving = Array.isArray(servingData) ? servingData[0] : servingData;

  return {
    calories: serving.calories,
    protein: serving.protein,
    fat: serving.fat,
    carbohydrate: serving.carbohydrate
  };
}

