import { loadQuestions, getTodaysQuestion } from './questionLoader.js';

window.backspace = backspace;
window.submitGuess = submitGuess; 

let selectedOptions = [];
let attempts = 0;
let options = [];
let correctAnswers = [];
let todaysQuestion;

// Initialize the game
document.addEventListener("DOMContentLoaded", async function() {
    const questions = await loadQuestions();
    if (!questions) return;

    todaysQuestion = getTodaysQuestion(questions);
    if (!todaysQuestion) return;

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
        alert('Congratulations! You guessed all correctly.');
        showSourceButton();
    } else if (attempts >= 5) {
        alert('Game over! Better luck next time.');
        showSourceButton();
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

function showSourceButton() {
    const sourceButton = document.createElement('button');
    sourceButton.classList.add('game-button');
    sourceButton.innerText = 'View Source Data';
    sourceButton.onclick = () => window.open(todaysQuestion.source, '_blank');
    
    // Add the button to the page (adjust the container ID as needed)
    const container = document.getElementById('game-container');
    container.appendChild(sourceButton);
} 