import { loadQuestions, getTodaysQuestion } from './questionLoader.js';

window.backspace = backspace;
window.submitGuess = submitGuess; 

let selectedOptions = [];
let attempts = 0;
let options = [];
let correctAnswers = [];
let todaysQuestion;
let gameOver = false;

// Initialize the game
document.addEventListener("DOMContentLoaded", async function() {
    // Help modal
    const helpBtn = document.getElementById('help-btn');
    const helpModal = document.getElementById('help-modal');
    const helpClose = document.getElementById('help-close');
    if (helpBtn && helpModal) {
        helpBtn.addEventListener('click', () => helpModal.classList.add('active'));
        helpClose.addEventListener('click', () => helpModal.classList.remove('active'));
        helpModal.addEventListener('click', (e) => {
            if (e.target === helpModal) helpModal.classList.remove('active');
        });
    }

    const questions = await loadQuestions();
    if (!questions) {
        document.getElementById('question').textContent = 'Failed to load questions. Please try again later.';
        return;
    }

    todaysQuestion = getTodaysQuestion(questions);
    if (!todaysQuestion) {
        document.getElementById('question').textContent = 'No question available for today. Come back tomorrow!';
        document.querySelector('.options-container').style.display = 'none';
        document.querySelector('.button-container').style.display = 'none';
        return;
    }

    options = todaysQuestion.options;
    correctAnswers = todaysQuestion.answers;
    
    // Update the question text
    document.getElementById('question').textContent = todaysQuestion.question;
    
    // Generate options
    const optionsDiv = document.getElementById('options');
    options.forEach(option => {
        const optionDiv = document.createElement('div');
        optionDiv.classList.add('option');
        optionDiv.innerText = option;
        optionDiv.onclick = () => selectOption(optionDiv, option);
        optionsDiv.appendChild(optionDiv);
    });

    // Highlight current attempt row
    highlightCurrentRow();

    // Button listeners
    document.getElementById('backspace').addEventListener('click', () => backspace());
    document.getElementById('submit').addEventListener('click', () => submitGuess());

    // Share button
    const shareBtn = document.getElementById('share-btn');
    if (shareBtn) {
        shareBtn.addEventListener('click', shareResult);
    }
});

function highlightCurrentRow() {
    // Remove active from all rows
    for (let i = 1; i <= 5; i++) {
        const row = document.getElementById(`attempt${i}`);
        if (row) row.classList.remove('active-row');
    }
    // Add active to current
    if (attempts < 5 && !gameOver) {
        const row = document.getElementById(`attempt${attempts + 1}`);
        if (row) row.classList.add('active-row');
    }
}

function showToast(message, duration = 1500) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
}

function selectOption(element, option) {
    if (gameOver) return;
    if (selectedOptions.length < 5 && !selectedOptions.includes(option)) {
        selectedOptions.push(option);
        element.classList.add('selected');
        updateCurrentGuess();
    }
}

function updateCurrentGuess() {
    const attemptDiv = document.getElementById(`attempt${attempts + 1}`);
    const feedbackCells = attemptDiv.querySelectorAll('.feedback');
    feedbackCells.forEach((cell, index) => {
        cell.innerText = selectedOptions[index] || '';
        if (selectedOptions[index]) {
            cell.classList.add('filled');
        } else {
            cell.classList.remove('filled');
        }
    });
}

function backspace() {
    if (gameOver) return;
    if (selectedOptions.length > 0) {
        const lastOption = selectedOptions.pop();
        document.querySelectorAll('.option').forEach(el => {
            if (el.innerText === lastOption) {
                el.classList.remove('selected');
            }
        });
        updateCurrentGuess();
    }
}

function submitGuess() {
    if (gameOver) return;
    if (selectedOptions.length !== 5) {
        showToast('Select 5 options first');
        // Shake the current row
        const row = document.getElementById(`attempt${attempts + 1}`);
        row.classList.add('shake');
        setTimeout(() => row.classList.remove('shake'), 600);
        return;
    }
    attempts++;
    const attemptDiv = document.getElementById(`attempt${attempts}`);
    const feedbackCells = attemptDiv.querySelectorAll('.feedback');

    // Reveal tiles one by one with a flip animation
    selectedOptions.forEach((option, index) => {
        setTimeout(() => {
            const feedback = feedbackCells[index];
            feedback.classList.add('reveal');

            let colorClass;
            if (option === correctAnswers[index]) {
                colorClass = 'tile-correct';
            } else if (correctAnswers.includes(option)) {
                colorClass = 'tile-present';
            } else {
                colorClass = 'tile-absent';
            }
            feedback.classList.add(colorClass);
            feedback.innerText = option;
            updateOptionColor(option, colorClass);
        }, index * 200);
    });

    // Capture current guess before clearing
    const currentGuess = [...selectedOptions];

    // After all tiles revealed, check win/lose
    setTimeout(() => {
        if (currentGuess.every((option, index) => option === correctAnswers[index])) {
            endGame(true);
        } else if (attempts >= 5) {
            endGame(false);
        } else {
            highlightCurrentRow();
        }
    }, 5 * 200 + 300);

    selectedOptions = [];
    document.querySelectorAll('.option').forEach(el => el.classList.remove('selected'));
}

function updateOptionColor(option, colorClass) {
    document.querySelectorAll('.option').forEach(el => {
        if (el.innerText === option) {
            // Priority: correct > present > absent (don't downgrade)
            if (el.classList.contains('tile-correct')) return;
            if (el.classList.contains('tile-present') && colorClass === 'tile-absent') return;
            el.classList.remove('tile-correct', 'tile-present', 'tile-absent');
            el.classList.add(colorClass);
        }
    });
}

function endGame(won) {
    gameOver = true;
    highlightCurrentRow();

    // Hide game controls with a fade
    const optionsContainer = document.querySelector('.options-container');
    const buttonContainer = document.querySelector('.button-container');
    optionsContainer.classList.add('fade-out');
    buttonContainer.classList.add('fade-out');

    setTimeout(() => {
        optionsContainer.style.display = 'none';
        buttonContainer.style.display = 'none';

        // Show results
        const resultsDiv = document.getElementById('game-results');
        resultsDiv.style.display = 'block';
        resultsDiv.classList.add('fade-in');

        const resultMessage = resultsDiv.querySelector('.result-message');
        if (won) {
            const messages = [
                'Genius!', 'Magnificent!', 'Impressive!', 'Splendid!', 'Great!'
            ];
            resultMessage.textContent = messages[attempts - 1] || 'Well done!';
            resultMessage.classList.add('result-win');
        } else {
            resultMessage.textContent = 'Better luck tomorrow!';
            resultMessage.classList.add('result-lose');
        }

        // Show correct answers
        const answersList = resultsDiv.querySelector('.correct-answers-list');
        correctAnswers.forEach((answer, index) => {
            const li = document.createElement('li');
            li.innerHTML = `<span class="answer-rank">${index + 1}.</span> ${answer}`;
            answersList.appendChild(li);
        });

        // Show source link
        if (todaysQuestion.source) {
            const sourceLink = resultsDiv.querySelector('.source-link');
            sourceLink.href = todaysQuestion.source;
            sourceLink.textContent = 'View Source';
            sourceLink.style.display = 'inline-block';
        }
    }, 400);
}

function shareResult() {
    // Build emoji grid
    const rows = [];
    for (let i = 1; i <= attempts; i++) {
        const row = document.getElementById(`attempt${i}`);
        const cells = row.querySelectorAll('.feedback');
        let rowStr = '';
        cells.forEach(cell => {
            if (cell.classList.contains('tile-correct')) rowStr += '🟩';
            else if (cell.classList.contains('tile-present')) rowStr += '🟨';
            else if (cell.classList.contains('tile-absent')) rowStr += '⬛';
            else rowStr += '⬜';
        });
        rows.push(rowStr);
    }

    const won = document.querySelector('.result-win') !== null;
    const score = won ? `${attempts}/5` : 'X/5';
    const text = `Factle ${score}\n${rows.join('\n')}\nhttps://seandeloddere.github.io/factle.html`;

    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Copied to clipboard!', 2000);
        });
    } else {
        showToast('Share not supported', 2000);
    }
} 