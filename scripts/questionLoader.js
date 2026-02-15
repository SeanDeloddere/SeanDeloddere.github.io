async function loadQuestions() {
    try {
        const response = await fetch('/factle/questions.json');
        const data = await response.json();
        return data.questions;
    } catch (error) {
        console.error('Error loading questions:', error);
        return null;
    }
}

function getTodaysQuestion(questions) {
    const today = new Date();
    const dateStr = `${today.getFullYear()}-${(today.getMonth() + 1).toString().padStart(2, '0')}-${today.getDate().toString().padStart(2, '0')}`;
    
    const todaysQuestion = questions.find(q => q.date === dateStr);
    
    if (!todaysQuestion) {
        console.error('No question found for today:', dateStr);
        return null;
    }

    // Validate the question has required data
    if (!todaysQuestion.options || todaysQuestion.options.length === 0 ||
        !todaysQuestion.answers || todaysQuestion.answers.length === 0) {
        console.error('Question found but missing options or answers');
        return null;
    }

    // Create a copy of options array and shuffle it
    const shuffledOptions = [...todaysQuestion.options].sort(() => Math.random() - 0.5);

    return {
        question: todaysQuestion.question,
        options: shuffledOptions,
        answers: todaysQuestion.answers,
        source: todaysQuestion.source
    };
}

export { loadQuestions, getTodaysQuestion }; 