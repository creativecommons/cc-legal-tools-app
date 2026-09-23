const menuButton = document.querySelector('button.expand-menu');
const menuPanel = document.querySelector('.primary-menu');

if(menuButton !== null && menuPanel !== null) {
    menuButton.addEventListener('click', (event) => {
        menuPanel.classList.toggle('expand');
    });
}

const menusWithChildren = document.querySelectorAll('main > aside.sidebar nav > ul > li:has(ul) > a');

menusWithChildren.forEach((menu) => {
    const expandButton = document.createElement('button');
    expandButton.classList.add('expand');
    expandButton.classList.add('icon-replace');
    expandButton.classList.add('fa-angle-down');
    expandButton.textContent = 'Expand';

    menu.insertAdjacentElement("afterend", expandButton);
});


const collapsedButtons = document.querySelectorAll('button.expand');

collapsedButtons.forEach((expander) => {

    expander.parentElement.querySelector('ul').classList.toggle('hide');

    expander.addEventListener('click', (event) => {
        event.target.parentElement.querySelector('ul').classList.toggle('hide');
    });

});
