async function generateResponse() {

    const prompt = document.getElementById("prompt").value.trim();
    const result = document.getElementById("result");

    if (!prompt) {
        result.innerHTML = "Please enter a prompt first ✨";
        return;
    }

    result.innerHTML = "✦ Aimi is thinking...";

    

        if (data.success) {
            result.innerHTML = escapeHTML(data.answer)
                .replace(/\n/g, "<br>");
        } else {
            result.innerHTML = "Sorry, something went wrong 😕";
        }

    } catch (error) {

        console.error(error);

        result.innerHTML =
            "Unable to connect to Aimi. Please try again.";
    }
}


function setPrompt(text) {

    document.getElementById("prompt").value = text;

    document.getElementById("prompt").focus();

}


function escapeHTML(text) {

    const div = document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}