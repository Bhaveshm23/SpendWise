

document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');

    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    console.log(sidebarToggleBtn);  // Check if the element is found

    sidebarToggleBtn.addEventListener('click', function () {
        console.log('Toggle button clicked.'); 
        sidebar.classList.toggle('active');
        content.classList.toggle('active');
    });
});
