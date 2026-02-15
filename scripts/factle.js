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

    // Add button listeners as backup
    document.getElementById('backspace').addEventListener('click', () => {
        console.log("Backspace clicked via event listener");
        backspace();
    });
    document.getElementById('submit').addEventListener('click', () => {
        console.log("Submit clicked via event listener");
        submitGuess();
    });
});

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
    });
}

function backspace() {
    if (gameOver) return;
    console.log("Backspace called");
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
    console.log("Submit called");
    if (selectedOptions.length !== 5) {
        alert('Please select 5 options.');
        return;
    }
    attempts++;
    const attemptDiv = document.getElementById(`attempt${attempts}`);
    const feedbackCells = attemptDiv.querySelectorAll('.feedback');
    selectedOptions.forEach((option, index) => {
        const feedback = feedbackCells[index];
        if (option === correctAnswers[index]) {
            feedback.classList.add('green');
            updateOptionColor(option, 'green');
        } else if (correctAnswers.includes(option)) {
            feedback.classList.add('yellow');
            updateOptionColor(option, 'yellow');
        } else {
            feedback.classList.add('grey');
            updateOptionColor(option, 'grey');
        }
        feedback.innerText = option;
    });
    if (selectedOptions.every((option, index) => option === correctAnswers[index])) {
        endGame(true);
    } else if (attempts >= 5) {
        endGame(false);
    }
    selectedOptions = [];
    document.querySelectorAll('.option').forEach(el => el.classList.remove('selected'));
    updateCurrentGuess();
}

function updateOptionColor(option, color) {
    document.querySelectorAll('.option').forEach(el => {
        if (el.innerText === option) {
            el.classList.remove('green', 'yellow', 'grey');
            el.classList.add(color);
        }
    });
}

function endGame(won) {
    gameOver = true;

    // Hide game controls
    document.querySelector('.options-container').style.display = 'none';
    document.querySelector('.button-container').style.display = 'none';

    // Show results
    const resultsDiv = document.getElementById('game-results');
    resultsDiv.style.display = 'block';

    const resultMessage = resultsDiv.querySelector('.result-message');
    resultMessage.textContent = won
        ? `Congratulations! You got it in ${attempts} ${attempts === 1 ? 'guess' : 'guesses'}!`
        : 'Game over! Better luck tomorrow.';
    resultMessage.classList.add(won ? 'result-win' : 'result-lose');

    // Show correct answers
    const answersList = resultsDiv.querySelector('.correct-answers-list');
    correctAnswers.forEach((answer, index) => {
        const li = document.createElement('li');
        li.textContent = `${index + 1}. ${answer}`;
        answersList.appendChild(li);
    });

    // Show source link
    if (todaysQuestion.source) {
        const sourceLink = resultsDiv.querySelector('.source-link');
        sourceLink.href = todaysQuestion.source;
        sourceLink.style.display = 'inline-block';
    }
} 