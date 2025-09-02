
  window.addEventListener('scroll', function () {
    let navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) { // when scrolled more than 50px
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });

document.addEventListener("DOMContentLoaded", function () {
  const navLinks = document.querySelectorAll('.navbar .nav-link');

  navLinks.forEach(link => {
    link.addEventListener("click", function () {
      // Remove active from all
      navLinks.forEach(l => l.classList.remove("active"));
      // Add active to clicked link
      this.classList.add("active");
    });
  });
});

// user register OTP section

document.querySelectorAll(".otp-input").forEach((input, index, inputs) => {
  input.addEventListener("input", () => {
    if (input.value && index < inputs.length - 1) {
      inputs[index + 1].focus();
    }
  });
});





