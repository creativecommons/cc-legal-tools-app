/* Import and use the Explore CC component */
const cc_explore = Vue.createApp({});
cc_explore.use(CcGlobals);
cc_explore.mount("#explore-cc");

/* Import and use the CC Global Header component */
const cc_header = Vue.createApp({});
cc_header.use(CcGlobals);
cc_header.mount("#header-cc");

/* Import and use the CC Global Footer component */
const cc_footer = Vue.createApp({});
cc_footer.use(CcGlobals);
cc_footer.mount("#footer-cc");
