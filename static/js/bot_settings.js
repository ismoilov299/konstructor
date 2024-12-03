function openBotSettings(botId, username, token) {
    const modal = document.getElementById('botSettingsModal');
    const botUsernameElement = document.getElementById('botUsername');
    const tokenInput = document.getElementById('bot_token');

    botUsernameElement.textContent = username;
    tokenInput.value = token;
    modal.style.display = 'block';

    const closeBtn = modal.querySelector('.close');
    closeBtn.onclick = () => modal.style.display = 'none';

    window.onclick = (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    }
}

function saveBotSettings() {
    const token = document.getElementById('bot_token').value;
    const selectedModule = document.querySelector('input[name="module"]:checked');

    if (!selectedModule) {
        alert('Выберите модуль');
        return;
    }

    const formData = new FormData();
    formData.append('bot_token', token);
    formData.append('module', selectedModule.value);
    formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

    fetch('/update_bot_settings/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert(`Настройки успешно сохранены`);
            window.location.reload();
        } else {
            alert(data.message || 'Произошла ошибка');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Произошла ошибка при сохранении настроек');
    });
}