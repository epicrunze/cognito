/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        './src/**/*.{html,js,svelte,ts}',
        './node_modules/@skeletonlabs/skeleton/**/*.{html,js,svelte,ts}'
    ],
    theme: {
        extend: {
            colors: {
                'primary-dark': '#1B3C53',
                'primary': '#234C6A',
                'primary-light': '#456882',
                'background': '#E3E3E3',
                'surface': '#FFFFFF',
                'text-primary': '#1B3C53',
                'text-secondary': '#456882'
            }
        }
    },
    plugins: [require('@skeletonlabs/tw-plugin')]
};
