const healthButton = document.getElementById("health-button");
const visitsButton = document.getElementById("visits-button");
const healthOutput = document.getElementById("health-output");
const visitsOutput = document.getElementById("visits-output");

async function callApi(url, outputElement, button) {
  button.disabled = true;
  outputElement.textContent = "Loading...";

  try {
    const response = await fetch(url, {
      headers: {
        Accept: "application/json",
      },
    });

    const data = await response.json();

    if (!response.ok) {
      outputElement.textContent = JSON.stringify(
        {
          status: response.status,
          error: data,
        },
        null,
        2
      );
      return;
    }

    outputElement.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    outputElement.textContent = JSON.stringify(
      {
        message: "Request failed",
        error: error.message,
      },
      null,
      2
    );
  } finally {
    button.disabled = false;
  }
}

healthButton.addEventListener("click", () => {
  callApi("/api/health", healthOutput, healthButton);
});

visitsButton.addEventListener("click", () => {
  callApi("/api/visits", visitsOutput, visitsButton);
});
