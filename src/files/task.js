// specialized_task.js

function generateRandomNumber(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

const randomNumber = generateRandomNumber(1, 100);
console.log("Generated random number:", randomNumber);
