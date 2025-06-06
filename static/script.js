async function searchFood() {
  const query = document.getElementById('searchInput').value;
  const response = await fetch('/search', {
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

    let clickedOnce = false;
    let nutritionData = null;

    p.onclick = async () => {
      if (!clickedOnce) {
        // First click: fetch and display nutrition
        nutritionData = await getNutrition(food.food_id);
        if (!nutritionData) {
          nutritionDiv.innerHTML = '<i>Nutrition data not available.</i>';
        } else {
          nutritionDiv.innerHTML = `
            <ul>
              <li>Calories: ${nutritionData.calories}</li>
              <li>Protein: ${nutritionData.protein}g</li>
              <li>Fat: ${nutritionData.fat}g</li>
              <li>Carbs: ${nutritionData.carbohydrate}g</li>
            </ul>
            <small>Click again to select this food.</small>
          `;
        }
        nutritionDiv.style.display = 'block';
        clickedOnce = true;
      } else {
        // Second click: populate the form
        if (nutritionData) {
          document.getElementById('item').value = food.food_name;
          document.querySelector('input[name="calories"]').value = parseFloat(nutritionData.calories);
          document.querySelector('input[name="protein"]').value = parseFloat(nutritionData.protein);
          document.querySelector('input[name="carbs"]').value = parseFloat(nutritionData.carbohydrate);
          document.querySelector('input[name="fat"]').value = parseFloat(nutritionData.fat);
        }
      }
    };

    foodContainer.appendChild(p);
    foodContainer.appendChild(nutritionDiv);
    resultsDiv.appendChild(foodContainer);
  });
}

async function getNutrition(food_id) {
  const response = await fetch('/food_details', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ food_id })
  });

  const data = await response.json();

  const servingData = data.food?.servings?.serving;

  if (!servingData) return null;

  const serving = Array.isArray(servingData) ? servingData[0] : servingData;

  return {
    calories: serving.calories,
    protein: serving.protein,
    fat: serving.fat,
    carbohydrate: serving.carbohydrate
  };
}
