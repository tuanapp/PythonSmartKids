// emailService.js

function sendEmail(correctAnswers, incorrectAnswers, studyCounter) {
    // Prepare the email content
    const emailParams = {
        datetime: new Date(),
        from_name: 'Rehaab',
        to_name: "Admin", // Replace with the recipient's name
        to_email: "kdx.shaggy@gmail.com", // Replace with the recipient's email
        subject: "Word Game Report from",
        message: `Here is the report of your session:
        \n\nCorrect Answers: ${correctAnswers.length}
        \nIncorrect Answers: ${incorrectAnswers.length}
        \n\nDetails:\n${incorrectAnswers.join('\n')}
        \n\nstudyCounter:\n${studyCounter}`
    };

    debugger
    // Send the email using EmailJS
    emailjs.send("service_qlmiznm", "template_1b1sx9n", emailParams)
        .then(response => {
            console.log("Email sent successfully!", response.status, response.text);
            Toastify({
                text: "Report emailed successfully!",
                duration: 5000,
                close: true,
                gravity: "top",
                position: "right",
                style: {
                    background: "linear-gradient(to right, #00b09b, #96c93d)",
                },
            }).showToast();
        })
        .catch(error => {
            console.error("Failed to send email:", JSON.stringify(error));
            Toastify({
                text: "Failed to send report email. "+ JSON.stringify(error),
                duration: 5000,
                close: true,
                gravity: "top",
                position: "right",
                style: {
                    background: "linear-gradient(to right, #ff5f6d, #ffc371)",
                },
            }).showToast();
        });
}