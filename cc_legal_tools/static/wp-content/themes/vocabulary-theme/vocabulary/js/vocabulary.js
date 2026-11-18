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

// handle pushdown banner hide for a time functionality
const showNotice = localStorage.getItem('showNotice');
const currentTime = Date.now();
const noticeHiddenAt = localStorage.getItem('noticeHiddenAt'); // set to time when clicked.
// const hideNoticeInterval = 20000; // set to a seconds (integer)
const hideNoticeInterval = 3600000; // set to a seconds (integer)
const elapsedHiddenTime = (currentTime - noticeHiddenAt); // time between now and noticeHiddenAt in ms

if(showNotice === 'false' && elapsedHiddenTime <= hideNoticeInterval){
  document.querySelector('article.attention.medium-importance').classList.toggle('hide');
  // console.log('notice stays hidden');
  // console.log(elapsedHiddenTime);
} else {
    localStorage.setItem('showNotice', 'true');
    localStorage.setItem('noticeHiddenAt', 0);
    // console.log('notice unhides');
    // console.log(elapsedHiddenTime);
}

document.querySelector('#closeNotice').addEventListener('click', (event) => {
  document.querySelector('article.attention.medium-importance').classList.toggle('hide');
  localStorage.setItem('noticeHiddenAt', currentTime);
  localStorage.setItem('showNotice', 'false');
  // console.log('notice hides');
});
