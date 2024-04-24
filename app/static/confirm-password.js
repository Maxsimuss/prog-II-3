document.getElementById("password").addEventListener("keyup", check);
document.getElementById("confirmPassword").addEventListener("keyup", check);

function check() {
    let val1 = document.getElementById("password").value;
    let val2 = document.getElementById("confirmPassword").value;

    document.getElementById("submit").disabled = val1.length < 6 || val1 != val2;
}